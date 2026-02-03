import base64
import io
import re
import zipfile
import requests
from difflib import SequenceMatcher
import streamlit as st

@st.cache_data(show_spinner=False)
def fetch_image_as_base64(img_url: str, referer_url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": referer_url}
        resp = requests.get(img_url, headers=headers, timeout=10)
        return f"data:image/jpeg;base64,{base64.b64encode(resp.content).decode()}"
    except:
        return ""

def create_images_zip(urls, referer):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, u in enumerate(urls):
            try:
                r = requests.get(u, headers={"Referer": referer}, timeout=10)
                zf.writestr(f"image_{i+1}.jpg", r.content)
            except: continue
    return buf.getvalue()

def make_diff_html(a, b):
    s_a = [s.strip() for s in re.split(r'([。！？\n]+)', a) if s.strip()]
    s_b = [s.strip() for s in re.split(r'([。！？\n]+)', b) if s.strip()]
    sm = SequenceMatcher(None, s_a, s_b)
    l_res, r_res = [], []
    style = "padding:8px; margin:2px; border-radius:4px; line-height:1.6; min-height:1.5em; color: #1e293b;"
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for i in range(i1, i2):
                row = f'<div style="{style}">{s_a[i]}</div>'
                l_res.append(row); r_res.append(row)
        elif tag == 'delete':
            for i in range(i1, i2):
                l_res.append(f'<div style="{style} background-color:#fee2e2; border:1px solid #ef4444;">{s_a[i]}</div>')
                r_res.append(f'<div style="{style} opacity:0.3;"> </div>')
        elif tag == 'insert':
            for j in range(j1, j2):
                r_res.append(f'<div style="{style} background-color:#dcfce7; border:1px solid #22c55e;">{s_b[j]}</div>')
                l_res.append(f'<div style="{style} opacity:0.3;"> </div>')
        elif tag == 'replace':
            for i in range(i1, i2):
                l_res.append(f'<div style="{style} background-color:#fef9c3; border:1px solid #eab308;">{s_a[i]}</div>')
            for j in range(j1, j2):
                r_res.append(f'<div style="{style} background-color:#fef9c3; border:1px solid #eab308;">{s_b[j]}</div>')
    return "".join(l_res), "".join(r_res)
