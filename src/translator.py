from typing import List
import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator

def translate_paragraphs(paragraphs: List[dict], engine_name="Google", source_lang="auto"):
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

