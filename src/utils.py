import base64
import io
import re
import zipfile
import requests
from difflib import SequenceMatcher
import streamlit as st
from PIL import Image

from typing import Optional

@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False)
def fetch_image_data_v10(img_url: str, referer_url: str) -> tuple[Optional[str], str, str]:
    try:
        if referer_url.startswith("https://mp.weixin.qq.com"):
             # WeChat specialized headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://mp.weixin.qq.com/",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
        else:
             headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": referer_url,
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
            }
        
        resp = requests.get(img_url, headers=headers, timeout=10)
        
        if resp.status_code != 200 or len(resp.content) < 100:
            return None, "", ""

        # Validation 1: Strict Content-Type check
        content_type = resp.headers.get('Content-Type', '').lower()
        if 'image' not in content_type:
            return None, "", ""

        # Validation 2: Try to open with PIL to verify integrity and get size
        try:
            image = Image.open(io.BytesIO(resp.content))
            width, height = image.size
            dims = f"{width}x{height}"
            fmt = image.format or "IMG"
            image.verify()
        except Exception:
            return None, "", ""

        # Mapping based on Content-Type or simple extension fallback
        if 'png' in content_type:
            mime = 'image/png'
        elif 'gif' in content_type:
            mime = 'image/gif'
        elif 'webp' in content_type:
            mime = 'image/webp'
        elif 'svg' in content_type:
            mime = 'image/svg+xml'
        else:
            mime = 'image/jpeg'
            
        return f"data:{mime};base64,{base64.b64encode(resp.content).decode()}", dims, fmt
    except Exception:
        return None, "", ""

def create_images_zip(urls, referer):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, u in enumerate(urls):
            try:
                r = requests.get(u, headers={"Referer": referer}, timeout=10)
                if r.status_code == 200:
                    try:
                        img = Image.open(io.BytesIO(r.content))
                        ext = (img.format or "JPG").lower()
                        # Normalize common extensions
                        if ext == "jpeg": ext = "jpg"
                    except:
                        ext = "jpg"
                    zf.writestr(f"image_{i+1}.{ext}", r.content)
            except: continue
    return buf.getvalue()

def make_diff_html(a, b):
    """Generate side-by-side diff HTML with guaranteed row alignment using table layout."""
    s_a = [s.strip() for s in re.split(r'([。！？\n]+)', a) if s.strip()]
    s_b = [s.strip() for s in re.split(r'([。！？\n]+)', b) if s.strip()]
    sm = SequenceMatcher(None, s_a, s_b)
    
    rows = []  # Will contain complete table rows
    
    # Cell style
    cell_style = "padding:12px 16px; line-height:1.8; min-height:2em; color:#1e293b; border-bottom:1px solid #f1f5f9; vertical-align:top; width:50%;"
    
    row_id = 0
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            # Same content in both
            for i in range(i1, i2):
                l_cell = f'<td style="{cell_style} background-color:#ffffff;">{s_a[i]}</td>'
                r_cell = f'<td style="{cell_style} background-color:#ffffff;">{s_a[i]}</td>'
                rows.append(f'<tr data-sync-id="diff-{row_id}">{l_cell}{r_cell}</tr>')
                row_id += 1
                
        elif tag == 'delete':
            # Content only in left (deleted)
            for i in range(i1, i2):
                l_cell = f'<td style="{cell_style} background-color:#fee2e2; border-left:3px solid #ef4444;">{s_a[i]}</td>'
                r_cell = f'<td style="{cell_style} background-color:#fafafa;"><span style="color:#94a3b8; font-style:italic;">（削除）</span></td>'
                rows.append(f'<tr data-sync-id="diff-{row_id}">{l_cell}{r_cell}</tr>')
                row_id += 1
                
        elif tag == 'insert':
            # Content only in right (inserted)
            for j in range(j1, j2):
                l_cell = f'<td style="{cell_style} background-color:#fafafa;"><span style="color:#94a3b8; font-style:italic;">（追加）</span></td>'
                r_cell = f'<td style="{cell_style} background-color:#dcfce7; border-left:3px solid #22c55e;">{s_b[j]}</td>'
                rows.append(f'<tr data-sync-id="diff-{row_id}">{l_cell}{r_cell}</tr>')
                row_id += 1
                
        elif tag == 'replace':
            # Content differs
            max_len = max(i2 - i1, j2 - j1)
            for idx in range(max_len):
                if idx < (i2 - i1):
                    l_content = s_a[i1 + idx]
                    l_cell = f'<td style="{cell_style} background-color:#fef3c7; border-left:3px solid #f59e0b;">{l_content}</td>'
                else:
                    l_cell = f'<td style="{cell_style} background-color:#fafafa;"></td>'
                
                if idx < (j2 - j1):
                    r_content = s_b[j1 + idx]
                    r_cell = f'<td style="{cell_style} background-color:#fef3c7; border-left:3px solid #f59e0b;">{r_content}</td>'
                else:
                    r_cell = f'<td style="{cell_style} background-color:#fafafa;"></td>'
                
                rows.append(f'<tr data-sync-id="diff-{row_id}">{l_cell}{r_cell}</tr>')
                row_id += 1
    
    # Wrap in table
    table_html = f'<table style="width:100%; border-collapse:collapse; table-layout:fixed;">{"".join(rows)}</table>'
    
    return table_html, ""  # Return table as left, empty string as right (not used)


    return table_html, ""  # Return table as left, empty string as right (not used)

# --- 言語検出ユーティリティ ---
from langdetect import detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException

def detect_language(text: str) -> str:
    """
    テキストの言語を検出する。
    戻り値: 'zh-cn', 'en', 'mixed', 'unknown' など。
    確率が低い場合や複数言語が拮抗している場合は 'mixed' を返す。
    """
    try:
        # 短すぎるテキストは検出精度が低いので除外または処理
        if not text or len(text.strip()) < 10:
            return "unknown"
            
        langs = detect_langs(text)
        if not langs:
            return "unknown"
            
        primary = langs[0]
        
        # 信頼度が低い、または混合している場合
        # 例: 中国語記事の中に英語の引用が多い場合などは mixed として自動検出（段落ごとの判定）に任せる
        if primary.prob < 0.95 and len(langs) > 1:
            return "mixed"
            
        return primary.lang
    except LangDetectException:
        return "unknown"
