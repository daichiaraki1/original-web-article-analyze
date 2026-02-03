from typing import List
import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator

def translate_paragraphs(paragraphs: List[dict]):
    translated_data = []
    total = len(paragraphs)
    status_area = st.empty()
    for i, p in enumerate(paragraphs):
        text = p.get("text", "")
        tag = p.get("tag", "p")
        status_area.markdown(f"⏳ **翻訳プロセス実行中:** {i+1}/{total} 段落目")
        res_text = text
        engine = "None"
        try:
            res_text = GoogleTranslator(source='auto', target='ja').translate(text)
            engine = "Google"
        except:
            try:
                res_text = MyMemoryTranslator(source='auto', target='ja-JP').translate(text)
                engine = "MyMemory"
            except:
                res_text = text
                engine = "Failed"
        translated_data.append({"text": str(res_text), "engine": engine, "tag": tag})
    status_area.empty()
    return translated_data
