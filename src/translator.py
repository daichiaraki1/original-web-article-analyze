from typing import List
import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator

def translate_paragraphs(paragraphs: List[dict], engine_name="Google", source_lang="auto"):
    translated_data = []
    total = len(paragraphs)
    status_area = st.empty()
    
    # Translator instances (init once if possible, but here for simplicity)
    # Using 'auto' -> 'ja'/ 'ja-JP'
    
    for i, p in enumerate(paragraphs):
        text = p.get("text", "")
        tag = p.get("tag", "p")
        
        # Status update
        status_area.markdown(f"""
            <div style="padding:10px; border-radius:5px; background-color:#f0f9ff; border:1px solid #bae6fd; color:#0369a1;">
                ⏳ <strong>翻訳プロセス実行中 ({engine_name}):</strong> {i+1}/{total} 段落目
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
                    # Fallback to MyMemory, try to guess or use provided source
                    mem_source = source_lang
                    if mem_source == 'auto': mem_source = 'zh-CN' # Fallback default
                    res_text = MyMemoryTranslator(source=mem_source, target='ja-JP').translate(text)
                    used_engine = "MyMemory (Fallback)"
                except:
                    res_text = text
                    used_engine = "Failed"
                    
        elif engine_name == "MyMemory":
            try:
                # MyMemory doesn't support 'auto' well, so if user chose auto, use zh-CN default or warn?
                # For now let's map auto -> zh-CN as that is the main use case, but if user selected English UI, passed 'en'
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
        
    status_area.empty()
    return translated_data
