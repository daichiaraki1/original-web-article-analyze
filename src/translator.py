from typing import List
import streamlit as st
import re
from deep_translator import GoogleTranslator, MyMemoryTranslator


def translate_paragraphs_chunked(paragraphs: List[dict], source_lang="auto", chunk_size=3):
    """
    チャンキング方式の翻訳: 複数段落をまとめて翻訳し、文脈を考慮した翻訳を実現
    番号付きマーカーを使用して段落を区切る
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
        chunks.append((i, chunk))  # (開始インデックス, チャンク) のタプル
    
    for chunk_idx, (start_idx, chunk) in enumerate(chunks):
        texts = [p.get("text", "") for p in chunk]
        tags = [p.get("tag", "p") for p in chunk]
        
        # 番号付きマーカーで連結
        # 例: "###1### 最初の段落 ###2### 二番目の段落 ###3### 三番目の段落"
        marked_parts = []
        for i, text in enumerate(texts):
            marker = f"###{start_idx + i + 1}###"
            marked_parts.append(f"{marker} {text}")
        combined_text = " ".join(marked_parts)
        
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
            
            if translated_combined is None:
                raise Exception("Translation returned None")
            
            print(f"[Chunking] Chunk {chunk_idx}: Translated = {translated_combined[:200]}...")
            
            # マーカーで分割（正規表現で番号マーカーを検索）
            # ###数字### のパターンを探す
            pattern = r'###(\d+)###'
            
            # マーカーの位置と番号を見つける
            matches = list(re.finditer(pattern, translated_combined))
            
            if len(matches) >= 1:
                # マーカーが見つかった場合
                translated_parts = []
                for i, match in enumerate(matches):
                    start_pos = match.end()
                    # 次のマーカーまで、または文字列の終わりまでを取得
                    if i + 1 < len(matches):
                        end_pos = matches[i + 1].start()
                    else:
                        end_pos = len(translated_combined)
                    
                    part = translated_combined[start_pos:end_pos].strip()
                    translated_parts.append(part)
                
                print(f"[Chunking] Found {len(matches)} markers, got {len(translated_parts)} parts")
                
                # 結果を追加
                for j in range(len(chunk)):
                    if j < len(translated_parts):
                        translated_data.append({
                            "text": translated_parts[j],
                            "engine": "Google (Chunking)",
                            "tag": tags[j]
                        })
                    else:
                        # マーカー数が足りない場合は個別翻訳
                        try:
                            single = GoogleTranslator(source=source_lang, target='ja').translate(texts[j])
                            translated_data.append({
                                "text": single if single else texts[j],
                                "engine": "Google (Chunking-Partial)",
                                "tag": tags[j]
                            })
                        except:
                            translated_data.append({
                                "text": texts[j],
                                "engine": "Failed",
                                "tag": tags[j]
                            })
            else:
                # マーカーが見つからない場合、全体を最初の段落として使用し、残りは個別翻訳
                print(f"[Chunking] No markers found, falling back")
                translated_data.append({
                    "text": translated_combined,
                    "engine": "Google (Chunking-NoMarker)",
                    "tag": tags[0]
                })
                for j in range(1, len(chunk)):
                    try:
                        single = GoogleTranslator(source=source_lang, target='ja').translate(texts[j])
                        translated_data.append({
                            "text": single if single else texts[j],
                            "engine": "Google (Fallback)",
                            "tag": tags[j]
                        })
                    except:
                        translated_data.append({
                            "text": texts[j],
                            "engine": "Failed",
                            "tag": tags[j]
                        })
                        
        except Exception as e:
            print(f"[Chunking] Error: {str(e)}")
            # エラー時は1段落ずつ
            for j, p in enumerate(chunk):
                try:
                    res = GoogleTranslator(source=source_lang, target='ja').translate(p.get("text", ""))
                    translated_data.append({
                        "text": res if res else p.get("text", ""),
                        "engine": "Google (Fallback)",
                        "tag": tags[j]
                    })
                except:
                    translated_data.append({
                        "text": p.get("text", ""),
                        "engine": "Failed",
                        "tag": tags[j]
                    })
    
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

