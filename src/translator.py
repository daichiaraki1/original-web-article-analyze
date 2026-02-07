from typing import List
import streamlit as st
import re
from deep_translator import GoogleTranslator, MyMemoryTranslator, DeeplTranslator

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
            # DeepL translation
            deepl_source = None
            if source_lang != 'auto':
                s_upper = source_lang.upper()
                if s_upper in ['ZH-CN', 'ZH-TW', 'ZH-HANS', 'ZH-HANT']:
                    deepl_source = 'zh'
                else:
                    deepl_source = s_upper
            
            # Check source != target (DeepL doesn't support JA -> JA)
            if deepl_source == 'JA':
                return text, "DeepL (Skipped: Source=Target)"
            
            # Construct init arguments
            init_args = {
                'api_key': deepl_api_key,
                'target': 'JA',
                'use_free_api': True
            }
            if deepl_source:
                init_args['source'] = deepl_source
            
            print(f"DEBUG: DeepL Init Args: {init_args}, Text len: {len(text)}")
            res = DeeplTranslator(**init_args).translate(text)
            return (res if res else text), "DeepL"
        except Exception as e:
            # Try Pro API
            try:
                # Re-construct args for PRO
                init_args = {
                    'api_key': deepl_api_key,
                    'target': 'JA',
                    'use_free_api': False
                }
                if deepl_source:
                    init_args['source'] = deepl_source
                
                res = DeeplTranslator(**init_args).translate(text)
                return (res if res else text), "DeepL (Pro)"
            except Exception as e:
                # エラー（Googleへのフォールバックは行わない）
                error_str = str(e)
                if "No support for the provided language" in error_str and "JA" in error_str:
                     return text, "DeepL (Skipped: Source=Target)"
                return text, f"DeepL (Failed: {error_str[:50]})"
    
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
    progress_bar = st.progress(0)
    status_area = st.empty()
    
    for i, p in enumerate(paragraphs):
        text = p.get("text", "")
        tag = p.get("tag", "p")
        
        # Update progress bar
        progress = (i + 1) / total
        progress_bar.progress(progress, text=f"翻訳中: {i+1}/{total} 段落")
        
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
    progress_bar.empty()
    status_area.empty()
    return translated_data
