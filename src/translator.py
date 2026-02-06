from typing import List
import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator

# チャンキング用の区切り文字（翻訳されにくい特殊マーカー）
PARAGRAPH_DELIMITER = " |||PARA||| "

def translate_paragraphs_chunked(paragraphs: List[dict], source_lang="auto", chunk_size=5):
    """
    チャンキング方式の翻訳: 複数段落をまとめて翻訳し、文脈を考慮した翻訳を実現
    """
    translated_data = []
    total = len(paragraphs)
    
    # Progress UI elements
    progress_bar = st.progress(0)
    status_area = st.empty()
    
    # チャンクに分割
    chunks = []
    for i in range(0, total, chunk_size):
        chunk = paragraphs[i:i + chunk_size]
        chunks.append(chunk)
    
    processed = 0
    
    for chunk_idx, chunk in enumerate(chunks):
        # チャンク内のテキストを区切り文字で連結
        texts = [p.get("text", "") for p in chunk]
        tags = [p.get("tag", "p") for p in chunk]
        combined_text = PARAGRAPH_DELIMITER.join(texts)
        
        # Update progress
        chunk_start = chunk_idx * chunk_size + 1
        chunk_end = min((chunk_idx + 1) * chunk_size, total)
        progress = chunk_end / total
        progress_bar.progress(progress, text=f"翻訳中: {chunk_end}/{total} 段落")
        
        status_area.markdown(f"""
            <div style="
                padding: 12px 16px;
                border-radius: 8px;
                background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                border: 1px solid #f59e0b;
                color: #92400e;
                font-weight: 500;
            ">
                <strong>Google (Chunking)</strong> で翻訳中... ({chunk_start}〜{chunk_end}/{total} 段落をまとめて処理)
            </div>
        """, unsafe_allow_html=True)
        
        try:
            # まとめて翻訳
            translated_combined = GoogleTranslator(source=source_lang, target='ja').translate(combined_text)
            
            # 区切り文字で分割
            translated_parts = translated_combined.split(PARAGRAPH_DELIMITER)
            
            # 分割数が元の段落数と一致しない場合の処理
            if len(translated_parts) != len(chunk):
                # フォールバック: 改行や類似パターンで分割を試みる
                # または元のテキストをそのまま返す
                alt_delimiters = ["|||PARA|||", "|||", "|PARA|"]
                for alt in alt_delimiters:
                    if alt in translated_combined:
                        translated_parts = translated_combined.split(alt)
                        break
                
                # それでも合わない場合は、翻訳結果を均等に分割
                if len(translated_parts) != len(chunk):
                    # 単純に翻訳結果全体を最初の段落に、残りは再翻訳
                    translated_parts = [translated_combined]
                    for j in range(1, len(chunk)):
                        try:
                            single_trans = GoogleTranslator(source=source_lang, target='ja').translate(texts[j])
                            translated_parts.append(single_trans)
                        except:
                            translated_parts.append(texts[j])
            
            # 結果を追加
            for j, trans_text in enumerate(translated_parts):
                if j < len(tags):
                    translated_data.append({
                        "text": str(trans_text).strip(),
                        "engine": "Google (Chunking)",
                        "tag": tags[j]
                    })
                    
        except Exception as e:
            # エラー時は1段落ずつフォールバック
            for j, p in enumerate(chunk):
                try:
                    res = GoogleTranslator(source=source_lang, target='ja').translate(p.get("text", ""))
                    translated_data.append({
                        "text": str(res),
                        "engine": "Google (Fallback)",
                        "tag": tags[j]
                    })
                except:
                    translated_data.append({
                        "text": p.get("text", ""),
                        "engine": "Failed",
                        "tag": tags[j]
                    })
        
        processed += len(chunk)
    
    # Clear progress UI when done
    progress_bar.empty()
    status_area.empty()
    return translated_data


def translate_paragraphs(paragraphs: List[dict], engine_name="Google", source_lang="auto"):
    """
    標準の1段落ずつ翻訳する方式
    """
    # チャンキング方式の場合は専用関数を呼び出す
    if engine_name == "Google (Chunking)":
        return translate_paragraphs_chunked(paragraphs, source_lang)
    
    translated_data = []
    total = len(paragraphs)
    
    # Progress UI elements
    progress_bar = st.progress(0)
    status_area = st.empty()
    
    for i, p in enumerate(paragraphs):
        text = p.get("text", "")
        tag = p.get("tag", "p")
        
        # Update progress bar
        progress = (i + 1) / total
        progress_bar.progress(progress, text=f"翻訳中: {i+1}/{total} 段落")
        
        # Status update with styled box
        status_area.markdown(f"""
            <div style="
                padding: 12px 16px;
                border-radius: 8px;
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border: 1px solid #bae6fd;
                color: #0369a1;
                font-weight: 500;
            ">
                <strong>{engine_name}</strong> で翻訳中... ({i+1}/{total} 段落)
            </div>
        """, unsafe_allow_html=True)
        
        res_text = text
        used_engine = "None"
        
        # Translation Logic based on selection
        if engine_name == "Google":
            try:
                res_text = GoogleTranslator(source=source_lang, target='ja').translate(text)
                used_engine = "Google"
            except:
                try:
                    # Fallback to MyMemory
                    mem_source = source_lang
                    if mem_source == 'auto': mem_source = 'zh-CN'
                    res_text = MyMemoryTranslator(source=mem_source, target='ja-JP').translate(text)
                    used_engine = "MyMemory (Fallback)"
                except:
                    res_text = text
                    used_engine = "Failed"
                    
        elif engine_name == "MyMemory":
            try:
                mem_source = source_lang
                if mem_source == 'auto': mem_source = 'zh-CN'
                res_text = MyMemoryTranslator(source=mem_source, target='ja-JP').translate(text)
                used_engine = "MyMemory"
            except:
                try:
                    res_text = GoogleTranslator(source=source_lang, target='ja').translate(text)
                    used_engine = "Google (Fallback)"
                except:
                    res_text = text
                    used_engine = "Failed"
        
        translated_data.append({"text": str(res_text), "engine": used_engine, "tag": tag})
    
    # Clear progress UI when done
    progress_bar.empty()
    status_area.empty()
    return translated_data

