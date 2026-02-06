from typing import List
import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator

# チャンキング用の区切り文字（翻訳されにくい特殊マーカー）
PARAGRAPH_DELIMITER = "\n[PARA]\n"

def translate_paragraphs_chunked(paragraphs: List[dict], source_lang="auto", chunk_size=5):
    """
    チャンキング方式の翻訳: 複数段落をまとめて翻訳し、文脈を考慮した翻訳を実現
    """
    translated_data = []
    total = len(paragraphs)
    
    if total == 0:
        return translated_data
    
    # Progress UI elements
    progress_bar = st.progress(0)
    status_area = st.empty()
    
    # チャンクに分割
    chunks = []
    for i in range(0, total, chunk_size):
        chunk = paragraphs[i:i + chunk_size]
        chunks.append(chunk)
    
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
            
            # Noneチェック
            if translated_combined is None:
                print(f"[Chunking] Translation returned None for chunk {chunk_idx}")
                raise Exception("Translation returned None")
            
            print(f"[Chunking] Chunk {chunk_idx}: Original delimiter count: {combined_text.count(PARAGRAPH_DELIMITER)}")
            print(f"[Chunking] Chunk {chunk_idx}: Translated text length: {len(translated_combined)}")
            
            # 区切り文字で分割（複数パターンを試す）
            translated_parts = []
            delimiter_patterns = ["[PARA]", "[パラ]", "【パラ】", "[PARA]\n", "\n[PARA]\n"]
            
            for pattern in delimiter_patterns:
                if pattern in translated_combined:
                    translated_parts = [p.strip() for p in translated_combined.split(pattern) if p.strip()]
                    print(f"[Chunking] Found delimiter '{pattern}', got {len(translated_parts)} parts")
                    break
            
            # 区切りが見つからない場合
            if not translated_parts:
                print(f"[Chunking] No delimiter found in translation, falling back to single paragraph translation")
                # 1段落ずつ翻訳にフォールバック
                for j, text in enumerate(texts):
                    try:
                        single_trans = GoogleTranslator(source=source_lang, target='ja').translate(text)
                        if single_trans:
                            translated_parts.append(single_trans)
                        else:
                            translated_parts.append(text)
                    except:
                        translated_parts.append(text)
            
            # 分割数が合わない場合の調整
            while len(translated_parts) < len(chunk):
                # 不足分は1段落ずつ翻訳
                idx = len(translated_parts)
                if idx < len(texts):
                    try:
                        single_trans = GoogleTranslator(source=source_lang, target='ja').translate(texts[idx])
                        translated_parts.append(single_trans if single_trans else texts[idx])
                    except:
                        translated_parts.append(texts[idx])
                else:
                    break
            
            # 結果を追加
            for j in range(len(chunk)):
                if j < len(translated_parts):
                    translated_data.append({
                        "text": str(translated_parts[j]).strip(),
                        "engine": "Google (Chunking)",
                        "tag": tags[j]
                    })
                else:
                    translated_data.append({
                        "text": texts[j],
                        "engine": "Google (Chunking - Partial)",
                        "tag": tags[j]
                    })
                    
        except Exception as e:
            print(f"[Chunking] Error in chunk {chunk_idx}: {str(e)}")
            # エラー時は1段落ずつフォールバック
            for j, p in enumerate(chunk):
                try:
                    res = GoogleTranslator(source=source_lang, target='ja').translate(p.get("text", ""))
                    translated_data.append({
                        "text": str(res) if res else p.get("text", ""),
                        "engine": "Google (Fallback)",
                        "tag": tags[j]
                    })
                except Exception as e2:
                    print(f"[Chunking] Fallback error: {str(e2)}")
                    translated_data.append({
                        "text": p.get("text", ""),
                        "engine": "Failed",
                        "tag": tags[j]
                    })
    
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

