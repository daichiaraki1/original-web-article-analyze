from typing import List
import streamlit as st
import re
import requests
import time
from deep_translator import GoogleTranslator, MyMemoryTranslator

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


def translate_single_text(text: str, engine_name: str, source_lang: str, deepl_api_key: str = None) -> tuple:
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
            trans, eng = _translate_chunk(chunk, engine_name, source_lang, deepl_api_key)
            translated_chunks.append(trans)
            if "Fallback" in eng or "Failed" in eng:
                final_engine = eng
        
        return " ".join(translated_chunks), final_engine
    else:
        return _translate_chunk(text, engine_name, source_lang, deepl_api_key)


def _translate_chunk(text: str, engine_name: str, source_lang: str, deepl_api_key: str = None) -> tuple:
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
    
    return text, "None"


def translate_paragraphs(paragraphs: List[dict], engine_name="Google", source_lang="auto", deepl_api_key: str = None):
    """
    段落ごとに翻訳する（長い段落は自動分割）
    """
    translated_data = []
    total = len(paragraphs)
    
    if total == 0:
        return translated_data
    
    # Progress UI elements
    progress_placeholder = st.empty()
    status_area = st.empty()
    
    for i, p in enumerate(paragraphs):
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
        res_text, used_engine = translate_single_text(text, engine_name, source_lang, deepl_api_key)
        
        translated_data.append({
            "text": str(res_text),
            "engine": used_engine,
            "tag": tag
        })
    
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

    with placeholder.container():
    
        if not api_key:
            return

        st.markdown("---")
        
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
            
            # Simplified Layout (No nested columns to avoid issues)
            st.markdown(f"**DeepL使用状況 (月次)**: {count:,} / {limit:,} 文字 ({percent:.1f}%)")
            
            # Refresh button (inline-ish or below)
            if st.button("🔄 更新", key="refresh_deepl_usage"):
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
