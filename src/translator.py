from typing import List
import streamlit as st
import json
import re
import requests
import time
from deep_translator import GoogleTranslator, MyMemoryTranslator
import google.generativeai as genai

# Google翻訳の文字数制限（安全マージンを取って4500文字）
CHAR_LIMIT = 4500


def split_text_by_sentences(text: str, max_chars: int = CHAR_LIMIT) -> List[str]:
    """
    テキストを文単位で分割し、各チャンクがmax_chars以下になるようにする
    日本語・中国語・英語の文末記号に対応
    """
    # 文末記号で分割（。！？.!? など）
    # 中国語の句読点も考慮
    sentence_pattern = r'([。！？\.\!\?；;]+)'
    
    parts = re.split(sentence_pattern, text)
    
    # 分割記号を前の文に結合
    sentences = []
    i = 0
    while i < len(parts):
        sentence = parts[i]
        # 次が区切り記号なら結合
        if i + 1 < len(parts) and re.match(sentence_pattern, parts[i + 1]):
            sentence += parts[i + 1]
            i += 2
        else:
            i += 1
        if sentence.strip():
            sentences.append(sentence.strip())
    
    # 文をチャンクにまとめる
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # 1文でも制限を超える場合はそのまま追加（APIに任せる）
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            chunks.append(sentence)
        # 追加しても制限内なら追加
        elif len(current_chunk) + len(sentence) + 1 <= max_chars:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
        # 制限を超える場合は現在のチャンクを確定して新しいチャンクを開始
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    
    # 残りのチャンクを追加
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks if chunks else [text]


def translate_single_text(text: str, engine_name: str, source_lang: str, deepl_api_key: str = None, gemini_api_key: str = None) -> tuple:
    """
    単一のテキストを翻訳する（文字数制限考慮）
    Returns: (translated_text, used_engine)
    """
    # 文字数チェック
    if len(text) > CHAR_LIMIT:
        # 文単位で分割
        chunks = split_text_by_sentences(text, CHAR_LIMIT)
        translated_chunks = []
        final_engine = engine_name
        
        for chunk in chunks:
            trans, eng = _translate_chunk(chunk, engine_name, source_lang, deepl_api_key, gemini_api_key)
            translated_chunks.append(trans)
            if "Fallback" in eng or "Failed" in eng:
                final_engine = eng
        
        return " ".join(translated_chunks), final_engine
    else:
        return _translate_chunk(text, engine_name, source_lang, deepl_api_key, gemini_api_key)


def _translate_chunk(text: str, engine_name: str, source_lang: str, deepl_api_key: str = None, gemini_api_key: str = None) -> tuple:
    """
    実際の翻訳処理（内部関数）
    """
    if engine_name == "Google":
        try:
            res = GoogleTranslator(source=source_lang, target='ja').translate(text)
            return (res if res else text), "Google"
        except:
            try:
                mem_source = source_lang if source_lang != 'auto' else 'zh-CN'
                res = MyMemoryTranslator(source=mem_source, target='ja-JP').translate(text)
                return (res if res else text), "MyMemory (Fallback)"
            except:
                return text, "Failed"
    
    elif engine_name == "DeepL":
        if not deepl_api_key:
            return text, "Failed (No API Key)"
        try:
            # DeepL Direct API Implementation
            # Determine endpoint and source mapping
            # DeepL source for Chinese is 'ZH' per docs
            # If auto, omit source_lang
            
            is_free = deepl_api_key.endswith(':fx')
            base_url = "https://api-free.deepl.com/v2/translate" if is_free else "https://api.deepl.com/v2/translate"
            
            params = {
                'text': text,
                'target_lang': 'JA'
            }
            
            headers = {
                'Authorization': f'DeepL-Auth-Key {deepl_api_key}'
            }
            
            if source_lang != 'auto':
                s_upper = source_lang.upper()
                if s_upper in ['ZH-CN', 'ZH-TW', 'ZH-HANS', 'ZH-HANT', 'ZH']:
                    params['source_lang'] = 'ZH'
                elif s_upper == 'JA':
                    return text, "DeepL (Skipped: Source=Target)"
                else:
                    params['source_lang'] = s_upper
            
            try:
                resp = requests.post(base_url, data=params, headers=headers, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    translations = data.get('translations', [])
                    if translations:
                        return translations[0].get('text', text), "DeepL"
                    else:
                        return text, "DeepL (Empty Response)"
                else:
                    return text, f"DeepL (Error: {resp.status_code} - {resp.text[:50]})"
                    
            except Exception as e:
                return text, f"DeepL (NetError: {str(e)[:50]})"
        except Exception as e:
            return text, f"DeepL (SetupError: {str(e)})"
    
    elif engine_name == "MyMemory":
        try:
            mem_source = source_lang if source_lang != 'auto' else 'zh-CN'
            res = MyMemoryTranslator(source=mem_source, target='ja-JP').translate(text)
            return (res if res else text), "MyMemory"
        except:
            try:
                res = GoogleTranslator(source=source_lang, target='ja').translate(text)
                return (res if res else text), "Google (Fallback)"
            except:
                return text, "Failed"
    
    elif engine_name == "Gemini":
        if not gemini_api_key:
            return text, "Failed (No API Key)"
        
        try:
            genai.configure(api_key=gemini_api_key)
            # Use the latest available model from user's list
            model = genai.GenerativeModel('gemini-3-flash-preview')
            
            # Safety settings to avoid blocking content
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                },
            ]

            prompt = f"Translate the following text into natural Japanese. Do not add any explanations or notes, just output the translation.\n\n{text}"
            
            response = model.generate_content(
                prompt,
                safety_settings=safety_settings
            )
            
            if response.text:
                return response.text.strip(), "Gemini"
            else:
                return text, "Gemini (Empty Response)"
                
        except Exception as e:
            # Revert to simple error return, remove UI error for production feel unless debugging needed
            # st.error(f"Gemini Error: {str(e)}") 
            return text, f"Gemini (Error: {str(e)})" # Show full error for now
    
    return text, "None"


def get_available_models(api_key: str):
    """
    List available Gemini models for the provided API key.
    """
    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return models
    except Exception as e:
        return [f"Error listing models: {str(e)}"]


def translate_batch_gemini(paragraphs: List[dict], source_lang: str, gemini_api_key: str, output_placeholder, status_area, model_name: str = "gemini-3-flash-preview", engine_label: str = "Gemini (Batch)", progress_placeholder=None):
    """
    Translate all paragraphs in a single batch request using line-based format for robustness.
    """
    if not paragraphs:
        return []

    # Prepare batch input with clear separators
    # JSON is fragile. We use a custom separator that is unlikely to appear in text.
    # But simple newline might be safest if we instruct properly.
    # Let's use "|||" as separator for input and output to be safe against newlines in text.
    
    texts = [p.get("text", "") for p in paragraphs]
    combined_text = "\n|||\n".join(texts)
    
    # Configure Gemini
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(model_name)
    
    # Safety settings to avoid blocking content (Apply here too!)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    # Prompt
    prompt = f"""
    You are a professional translator. 
    Translate the following text blocks into natural Japanese.
    The input blocks are separated by "|||".
    
    IMPORTANT: 
    1. Output MUST be separated by "|||" exactly matching the input structure.
    2. Do NOT output JSON. Just the translated text blocks.
    3. Maintain the order.
    4. If a block is empty or just whitespace, keep it empty in output.
    
    Input:
    {combined_text}
    """

    
    if progress_placeholder:
         progress_placeholder.info(f"{engine_label} 一括翻訳中... ({len(texts)} 段落)")
    else:
         status_area.info(f"{engine_label} 一括翻訳中... ({len(texts)} 段落)")
    if output_placeholder:
        output_placeholder.markdown(
            """
            <div style="
                color: #64748b; 
                font-size: 0.9em; 
                margin-bottom: 15px; 
                display: flex; 
                align-items: center; 
                gap: 8px;
                background-color: #f8fafc;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #e2e8f0;
            ">
                <div class="spinner">⏳</div>
                <div>Geminiで一括翻訳中... (しばらくお待ちください)</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    full_response_text = ""
    streaming_text = ""
    error_message = None

    try:
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            stream=True
        )
        
        # Stream response
        if output_placeholder:
             # Ensure it's a list for compatibility with verify
             placeholders = output_placeholder if isinstance(output_placeholder, list) else [output_placeholder]
        else:
             placeholders = []

        # Stream response
        accumulated_buffer = ""
        current_paragraph_index = 0
        
        for chunk in response:
            if chunk.text:
                full_response_text += chunk.text
                accumulated_buffer += chunk.text
                
                # Check for separators in the buffer
                while "|||" in accumulated_buffer:
                    # Found a complete paragraph
                    split_idx = accumulated_buffer.find("|||")
                    paragraph_text = accumulated_buffer[:split_idx].strip()
                    accumulated_buffer = accumulated_buffer[split_idx + 3:]
                    
                    # Update current placeholder with FINAL text
                    if current_paragraph_index < len(placeholders):
                        ph = placeholders[current_paragraph_index]
                         # Format nicely
                        formatted_text = f"<div style='color:#334155; line-height:1.8; font-size:15px; animation: fadeIn 0.5s;'>{paragraph_text}</div>"
                        # Extra CSS for fade-in
                        ph.markdown(f"""
                        <style>@keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}</style>
                        {formatted_text}
                        """, unsafe_allow_html=True)
                    
                    current_paragraph_index += 1
                
                # Update the CURRENT (incomplete) paragraph with streaming text
                if current_paragraph_index < len(placeholders):
                    ph = placeholders[current_paragraph_index]
                    # Show accumulating text for current paragraph
                    # To avoid jitter, we might want to only update periodically or clean it?
                    # Streamlit handles markdown updates reasonably well.
                    preview_text = accumulated_buffer.strip()
                    if preview_text:
                         ph.markdown(f"<div style='color:#334155; line-height:1.8; font-size:15px; opacity: 0.7;'>{preview_text}▌</div>", unsafe_allow_html=True)
                
    except Exception as e:
        error_message = str(e)
        
        # Friendly Error Message for Quota Exceeded (429)
        if "429" in error_message or "quota" in error_message.lower():
             # Try to extract "retry in XXs"
             wait_time_msg = "しばらく時間を置いてから再試行してください（数分程度）。"
             retry_match = re.search(r"retry in ([0-9\.]+)s", error_message)
             if retry_match:
                 wait_seconds = float(retry_match.group(1))
                 wait_time_msg = f"約 {int(wait_seconds) + 1} 秒待機してから再試行してください。"
             
             # Sophisticated HTML Error Message
             # Check if this is just a Title (h1) or small single item
             is_title = len(paragraphs) == 1 and paragraphs[0].get("tag") == "h1"
             
             if is_title:
                 # Simplified error for title to avoid duplication with body error
                 # Use HTML span that fits inside H3
                 error_message = f"<span style='color: #be123c; font-size: 0.7em; font-weight: normal;'>⚠️ タイトル翻訳失敗: {str(e)[:50]}...</span>"
             else:
                 error_message = f"""
                 <div style="
                    background-color: #fff1f2; 
                    border: 1px solid #fda4af; 
                    border-radius: 8px; 
                    padding: 16px; 
                    color: #be123c; 
                    font-family: sans-serif;
                    margin-bottom: 10px;
                 ">
                    <div style="display: flex; align-items: start; gap: 10px;">
                        <div style="font-size: 1.5em;">⚠️</div>
                        <div>
                             <div style="font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">Gemini 利用制限 (Quota)</div>
                             <div style="font-size: 0.9em; line-height: 1.6;">
                                 APIの利用制限に達しました。{wait_time_msg}
                             </div>
                             <div style="
                                 background-color: #ffffff;
                                 border: 1px solid #fecdd3;
                                 border-radius: 6px;
                                 padding: 10px;
                                 margin-top: 10px;
                                 font-size: 0.85em;
                                 color: #881337;
                             ">
                                 <strong>【対処法】</strong>
                                 <ul style="margin: 5px 0 0 18px; padding: 0;">
                                     <li>別のGoogleアカウントのAPIキーを使用する</li>
                                     <li>Google Cloudの有料プラン(Pay-as-you-go)を有効にする</li>
                                 </ul>
                             </div>
                            <details style="margin-top: 10px; font-size: 0.8em; color: #9f1239; opacity: 0.8; cursor: pointer;">
                                <summary style="margin-bottom: 5px;">詳細エラーを表示</summary>
                                <div style="word-break: break-all; padding: 10px; background: rgba(255,255,255,0.5); border-radius: 4px;">
                                    {str(e)}
                                </div>
                            </details>
                        </div>
                    </div>
                 </div>
                 """
        
        # Store full HTML error in session state for banner display
        st.session_state["v9_error_banner_html"] = error_message
        
        # Return a clean message for the result column
        column_error = f"""
        <div style="color: #be123c; font-weight: 500; font-size: 0.9em; padding: 10px; border: 1px dashed #fda4af; border-radius: 6px; background: #fff1f2;">
           ⚠️ 翻訳エラー (詳細は上部の警告を確認してください)
        </div>
        """
        
        if not full_response_text:
            # Failed completely at start. Return error as text for the first block so it persists.
            results = []
            for i, p in enumerate(paragraphs):
                if i == 0:
                    results.append({
                        "text": column_error, 
                        "engine": "Gemini (Error)",
                        "tag": "div"
                    })
                else:
                    results.append({
                        "text": "...", 
                        "engine": "Gemini (Error)",
                        "tag": "p"
                    })
            return results

    # Split by separator
    translated_texts = full_response_text.split("|||")
    
    # Clean up
    translated_texts = [t.strip() for t in translated_texts]  # Allow empty strings if valid
    
    # Handle length mismatch
    if len(translated_texts) < len(texts):
        shortage = len(texts) - len(translated_texts)
        suffix = f"<br><span style='color:red; font-size:0.8em;'>⚠️ 翻訳停止 (詳細エラーは上部に表示)</span>" if error_message else " (中断)"
        if error_message:
             # If we have partial results but also an error, we should inject the error message somewhere visible.
             # Maybe append it to the last valid text or the first text?
             # For now, if we have partials, status_area IS useful.
             # But user wants single area.
             # Let's append the HTML error to the *next* block (the first failed one) to show where it stopped.
             translated_texts.append(error_message) # This becomes the first "missing" block
             shortage -= 1 # We filled one
             
        translated_texts.extend([f"..."] * shortage)
    elif len(translated_texts) > len(texts):
         translated_texts = translated_texts[:len(texts)]
    
    results = []
    ui_accumulated_text = ""
    
    for i, p in enumerate(paragraphs):
        t_text = translated_texts[i]
        
        # Detect if this specific item is the error message (for partial failure)
        current_engine = engine_label
        if error_message and t_text == error_message:
            current_engine = "Gemini (Error)"
        
        item = {
            "text": t_text,
            "engine": current_engine,
            "tag": p.get("tag", "p")
        }
        results.append(item)
        
        tag = p.get("tag", "p")
        header_prefix = "## " if tag == 'h2' else "### " if tag == 'h3' else ""
        ui_accumulated_text += f"\n\n{header_prefix}{t_text}\n\n"

    if output_placeholder:
         output_placeholder.markdown(ui_accumulated_text)

    if error_message:
        # Error is already in the results text, so just log or show a small warning if needed
        # But user wants NO duplication.
        # status_area.error(...) -> Removed
        pass
    else:
        status_area.success(f"Gemini (Batch) 翻訳完了！")
        
    return results


def translate_paragraphs(paragraphs: List[dict], engine_name="Google", source_lang="auto", deepl_api_key: str = None, gemini_api_key: str = None, output_placeholder=None, model_name=None, progress_placeholder=None, item_id_prefix=None, status_placeholder=None):
    """
    段落ごとに翻訳する（長い段落は自動分割）
    output_placeholder: Streamlit placeholder to render results incrementally
    status_placeholder: Streamlit placeholder to render status messages (moved to top)
    """
    translated_data = []
    total = len(paragraphs)
    
    if total == 0:
        return translated_data
    
    # Progress UI elements
    # If output_placeholder is provided, we might want to render the full table there
    # But constructing the full table incrementally is complex.
    # Instead, we can render a simple list or markdown of what's done so far.
    # A better approach for "pre-view" is just printing the text.
    
    progress_placeholder = progress_placeholder if progress_placeholder else st.empty()
    status_area = status_placeholder if status_placeholder else st.empty()
    
    # Gemini Optimization: Batch Translation
    # If engine is Gemini, we use a single request (or few chunks) to avoid Rate Limits (15 RPM / 20 RPD)
    if "Gemini" in engine_name:
        # Determine model name
        gemini_model_name = model_name  # Start with argument if provided
        
        # 1. Parse "Gemini:model" format (overrides argument if present)
        if ":" in engine_name:
            gemini_model_name = engine_name.split(":", 1)[1]
        
        # 2. Parse "Gemini (model)" format (overrides argument if present)
        match = re.search(r"Gemini \((.*?)\)", engine_name)
        if match:
            captured = match.group(1)
            # Map aliases
            if captured == "gemini-3-flash":
                gemini_model_name = "gemini-3-flash-preview"
            elif captured != "Batch": # Ignore "Batch" label
                gemini_model_name = captured

        # Fallback to default if no valid model name was determined
        if not gemini_model_name:
             gemini_model_name = "gemini-2.5-flash" # Use 2.5 flash as safe default per user feedback

        # Exception handling is done inside translate_batch_gemini
        return translate_batch_gemini(paragraphs, source_lang, gemini_api_key, output_placeholder, status_area, model_name=gemini_model_name, engine_label=f"Gemini ({gemini_model_name})", progress_placeholder=progress_placeholder)

    # ... (Original loop for other engines)
    
    # Header for streaming view - ONY if single placeholder
    if output_placeholder and not isinstance(output_placeholder, list):
        output_placeholder.markdown("### 翻訳プレビュー (生成中...)")
    
    streaming_text = ""

    for i, p in enumerate(paragraphs):
        # ... (rest of the loop)
        text = p.get("text", "")
        tag = p.get("tag", "p")
        
        # Update custom progress bar
        progress = (i + 1) / total
        percent = int(progress * 100)
        
        bar_html = f"""
        <div style="margin-bottom: 5px; font-weight: bold; color: #475569;">翻訳中: {i+1}/{total} 段落</div>
        <div style="
            background-color: #f1f5f9;
            width: 100%;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 15px;
        ">
            <div style="
                background-color: #3b82f6;
                width: {percent}%;
                height: 100%;
                border-radius: 4px;
                transition: width 0.3s ease;
            "></div>
        </div>
        """
        progress_placeholder.markdown(bar_html, unsafe_allow_html=True)
        
        # 長文の場合は分割処理中であることを表示
        char_info = f" ({len(text)}文字)" if len(text) > CHAR_LIMIT else ""
        status_area.markdown(f"""
            <div style="
                padding: 12px 16px;
                border-radius: 8px;
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border: 1px solid #bae6fd;
                color: #0369a1;
                font-weight: 500;
            ">
                <strong>{engine_name}</strong> で翻訳中... ({i+1}/{total} 段落){char_info}
            </div>
        """, unsafe_allow_html=True)
        
        # 翻訳実行（長文は自動分割）
        # Geminiの場合はレート制限対策として少し待機
        if engine_name == "Gemini":
            time.sleep(2.0) # Rate limit wait
        
        res_text, used_engine = translate_single_text(text, engine_name, source_lang, deepl_api_key, gemini_api_key)
        
        # エラー判定
        is_error = False
        if engine_name == "Gemini" and ("Error" in used_engine or "Failed" in used_engine):
             is_error = True
             status_area.error(f"翻訳が中断されました: {used_engine}")
        
        # Append to result list
        item = {
            "text": str(res_text),
            "engine": used_engine,
            "tag": tag
        }
        translated_data.append(item)

        # Update Streaming UI
        if output_placeholder:
            if isinstance(output_placeholder, list):
                # Row-by-row update
                if i < len(output_placeholder):
                    ph = output_placeholder[i]
                    # Format nicely with consistent style
                    # Apply simple card style for consistency
                    # Use item_id_prefix if available to support JS alignment
                    div_id = f'{item_id_prefix}-{i}'
                    formatted_text = f"""<div id="{div_id}" class="trans-paragraph-block" style='color:#334155; line-height:1.6; font-size:15px; animation: fadeIn 0.5s;'>{res_text}</div>"""
                    ph.markdown(formatted_text, unsafe_allow_html=True)
            else:
                # Single container update (Legacy)
                if tag == 'h2':
                    streaming_text += f"\n\n## {res_text}\n\n"
                elif tag == 'h3':
                    streaming_text += f"\n\n### {res_text}\n\n"
                else:
                    streaming_text += f"\n\n{res_text}\n\n"
                
                # Show current state
                with output_placeholder.container():
                    st.markdown(streaming_text)
                    if is_error:
                        st.error(f"⚠️ エラーにより中断: {used_engine}")

        if is_error:
             break

    # Clear progress UI when done
    progress_placeholder.empty()
    status_area.empty()
    return translated_data


def get_deepl_usage(deepl_api_key: str) -> dict:
    """
    DeepL APIの使用状況を取得する
    Returns: {'character_count': int, 'character_limit': int} or {'error': str}
    """
    if not deepl_api_key:
        return {'error': 'API Key is empty'}
    
    is_free = deepl_api_key.endswith(':fx')
    base_url = "https://api-free.deepl.com/v2/usage" if is_free else "https://api.deepl.com/v2/usage"
    
    headers = {
        'Authorization': f'DeepL-Auth-Key {deepl_api_key}'
    }
    
    try:
        resp = requests.get(base_url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # character_count and character_limit are standard fields
            return {
                'character_count': data.get('character_count', 0),
                'character_limit': data.get('character_limit', 0)
            }
        else:
            return {'error': f"Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {'error': f"NetError: {str(e)}"}


def render_deepl_usage_ui(api_key: str, placeholder=None):
    """
    DeepL使用状況を表示するUIコンポーネント
    placeholder: 表示先のst.empty()またはst.container()
    """
    if placeholder is None:
        placeholder = st.container()

    # FORCE CLEAR: Verify unique rendering
    placeholder.empty()

    with placeholder.container():
        
        if not api_key:
            return

        # st.markdown("---") # Removed for compact display
        
        # ... (cache logic) ...
        if "deepl_usage_cache" not in st.session_state:
            with st.spinner("使用状況を取得中..."):
                st.session_state["deepl_usage_cache"] = get_deepl_usage(api_key)
        
        usage = st.session_state["deepl_usage_cache"]
        
        if "error" in usage:
            # ... error handling ...
            st.error(f"取得失敗: {usage['error']}")
            if st.button("再試行", key="retry_deepl_usage"):
                 if "deepl_usage_cache" in st.session_state:
                     del st.session_state["deepl_usage_cache"]
                 st.rerun()
        else:
            count = usage['character_count']
            limit = usage['character_limit']
            percent = (count / limit * 100) if limit > 0 else 0
            
            # Layout: Text, then Button below
            st.markdown(f"**DeepL使用状況 (月次)**: {count:,} / {limit:,} 文字 ({percent:.1f}%)")
            
            # Refresh button (Text instead of Emoji per user request)
            if st.button("更新", key="refresh_deepl_usage", help="使用状況を更新"):
                if "deepl_usage_cache" in st.session_state:
                    del st.session_state["deepl_usage_cache"]
                st.rerun()

            
            # カスタムプログレスバー (背景グレー、使用率ブルー)
            bar_html = f"""
            <div style="
                background-color: #f1f5f9;
                width: 100%;
                height: 8px;
                border-radius: 4px;
                margin-top: 5px;
                overflow: hidden;
            ">
                <div style="
                    background-color: #3b82f6;
                    width: {min(percent, 100)}%;
                    height: 100%;
                    border-radius: 4px;
                "></div>
            </div>
            """
            st.markdown(bar_html, unsafe_allow_html=True)

        # APIキー設定済み表示
        st.markdown(f"""
            <div style="font-size: 0.8em; color: #22c55e; margin-top: 5px;">
                ✓ APIキー設定済み（{api_key[:8]}...）
            </div>
        """, unsafe_allow_html=True)
