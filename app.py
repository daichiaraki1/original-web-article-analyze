import textwrap
import datetime
import streamlit as st
import streamlit.components.v1 as components
from src.scraper import load_article_v9
import sys
import importlib
# Force reload to clear stale cache
if 'src.translator' in sys.modules:
    importlib.reload(sys.modules['src.translator'])

from src.translator import translate_paragraphs, get_deepl_usage, render_deepl_usage_ui, get_available_models, ocr_and_translate_image
from src.article_generator import generate_article
from st_copy_to_clipboard import st_copy_to_clipboard
from src.utils import create_images_zip, fetch_image_data_v10, make_diff_html, detect_language

import extra_streamlit_components as stx
import base64
import os
ICON_CIRCLE_CHECK_OUTLINE = "data:image/svg+xml;base64," + base64.b64encode(b"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#94a3b8' stroke-width='1.5'>
  <circle cx='12' cy='12' r='10'/>
  <path d='M8 12l2.5 2.5L16 9' stroke-linecap='round' stroke-linejoin='round'/>
</svg>
""").decode()

ICON_CIRCLE_CHECK_SOLID = "data:image/svg+xml;base64," + base64.b64encode(b"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='#3b82f6' stroke='none'>
  <circle cx='12' cy='12' r='11'/>
  <path d='M8 12l2.5 2.5L16 9' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='none'/>
</svg>
""").decode()

ICON_DOWNLOAD_TRAY = "data:image/svg+xml;base64," + base64.b64encode(b"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#64748b' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'>
  <path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/>
  <polyline points='7 10 12 15 17 10' />
  <line x1='12' y1='15' x2='12' y2='3' />
</svg>
""").decode()

ICON_COPY_SVG = "data:image/svg+xml;base64," + base64.b64encode(b"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#64748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
  <rect x='9' y='9' width='13' height='13' rx='2' ry='2'></rect>
  <path d='M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1'></path>
</svg>
""").decode()

# Load and encode copy icon (global)
copy_icon_b64 = ""
icon_path = os.path.join(os.path.dirname(__file__), "copy_icon.png")
if os.path.exists(icon_path):
    with open(icon_path, "rb") as f:
        copy_icon_b64 = base64.b64encode(f.read()).decode()

copy_icon_html = f"data:image/png;base64,{copy_icon_b64}" if copy_icon_b64 else ""

def render_copy_header(title, text_to_copy, key_suffix=""):
    """
    Renders a unified header with a title and a premium copy button.
    Uses st.components.v1.html for a styleable JS-based copy button.
    """
    # Escape special characters for JS string literal
    safe_text = text_to_copy.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n").replace("\r", "\\r")
    
    # Determine icon markup (Always use SVG for transparency and quality)
    icon_markup = f'<img src="{ICON_COPY_SVG}" id="custom-icon-{key_suffix}" style="width: 18px; height: 18px; object-fit: contain; vertical-align: middle;">'

    html_code = f"""
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #f1f5f9;
        padding: 0 16px;
        border-radius: 10px 10px 0 0;
        height: 48px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        box-sizing: border-box;
    ">
        <div style="font-weight: 700; color: #475569; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px;">{title}</div>
        <button id="copy-btn-{key_suffix}" style="
            display: flex;
            align-items: center;
            justify-content: center;
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 6px;
            width: 32px;
            height: 32px;
            cursor: pointer;
            transition: all 0.2s;
            padding: 0;
            outline: none;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: -10px; /* Aligned with 0.75rem header text */
        " title="コピー">
            {icon_markup}
            <span id="copy-check-{key_suffix}" style="display: none; color: #22c55e; font-size: 18px; font-weight: bold;">✓</span>
        </button>
    </div>
    <script>
        const btn = document.getElementById('copy-btn-{key_suffix}');
        const iconNormal = document.getElementById('copy-icon-{key_suffix}');
        const iconCustom = document.getElementById('custom-icon-{key_suffix}');
        const check = document.getElementById('copy-check-{key_suffix}');
        
        btn.onclick = function() {{
            const textArea = document.createElement("textarea");
            textArea.value = `{safe_text}`;
            document.body.appendChild(textArea);
            textArea.select();
            try {{
                document.execCommand('copy');
                // Visual feedback
                if (iconNormal) iconNormal.style.display = 'none';
                if (iconCustom) iconCustom.style.display = 'none';
                check.style.display = 'inline';
                btn.style.borderColor = '#22c55e';
                btn.style.backgroundColor = '#f0fdf4';
                
                setTimeout(() => {{
                    if (iconNormal) iconNormal.style.display = 'inline';
                    if (iconCustom) iconCustom.style.display = 'inline';
                    check.style.display = 'none';
                    btn.style.borderColor = '#e2e8f0';
                    btn.style.backgroundColor = '#ffffff';
                }}, 2000);
            }} catch (err) {{
                console.error('Copy failed:', err);
            }}
            document.body.removeChild(textArea);
        }};

        btn.onmouseover = function() {{
            if (check.style.display === 'none') {{
                btn.style.borderColor = '#3b82f6';
                btn.style.backgroundColor = '#f0f9ff';
            }}
        }};
        btn.onmouseout = function() {{
            if (check.style.display === 'none') {{
                btn.style.borderColor = '#e2e8f0';
                btn.style.backgroundColor = '#ffffff';
            }}
        }};
    </script>
    """
    components.html(html_code, height=48)

# --- メイン UI ---
def main():
    st.set_page_config(layout="wide", page_title="メディア解析ツール")

    # Initialize Cookie Manager AFTER page config
    # Use a fixed key to ensure component stability across reruns
    cookie_manager = stx.CookieManager(key="v9_cookie_manager")
    
    # Check for cookie-stored API keys on load
    cookies = cookie_manager.get_all()
    # print(f"DEBUG: Cookies loaded: {cookies}", flush=True) 
    
    # DeepL
    cookie_key = cookies.get("deepl_api_key_cookie") if cookies else None
    if cookie_key and not st.session_state.get("deepl_api_key"):
        st.session_state["deepl_api_key"] = cookie_key

    # Gemini
    cookie_gemini = cookies.get("gemini_v9_key") if cookies else None
    if cookie_gemini and not st.session_state.get("gemini_api_key"):
        st.session_state["gemini_api_key"] = cookie_gemini
    
    # Gemini Model Selection Persistence
    cookie_gemini_model = cookies.get("gemini_v9_model") if cookies else None
    if cookie_gemini_model and "gemini_model_setting" not in st.session_state:
        st.session_state["gemini_model_setting"] = cookie_gemini_model
        st.session_state["gemini_label_current"] = f"Gemini ({cookie_gemini_model})"
    elif "gemini_label_current" not in st.session_state:
        st.session_state["gemini_label_current"] = "Gemini (gemini-2.5-flash)"
    
    # Debug Cookies
    # st.write(f"DEBUG COOKIES: {cookie_manager.get_all()}")
    if "sel_imgs" not in st.session_state:
        st.session_state.sel_imgs = set()
    if "s_url_v9" not in st.session_state:
        st.session_state.s_url_v9 = ""
    if "c_url_v9" not in st.session_state:
        st.session_state.c_url_v9 = ""

    st.markdown(f"""
    <style>
        /* 1. 基本設定と白モードの徹底強制 */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {{
            background-color: #f8fafc !important;
            color: #1e293b !important;
        }}

        /* 2. 入力欄: 徹底的に白固定 & フォーカス時のグレー防止 */
        input[type="text"], 
        [data-testid="stTextInput"] div,
        [data-baseweb="input"],
        [data-baseweb="base-input"] {{
            background-color: #ffffff !important;
            color: #1e293b !important;
            border-color: #cbd5e1 !important;
        }}
        /* フォーカス時も白を維持 */
        [data-baseweb="base-input"]:focus-within {{
            background-color: #ffffff !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
        }}
        
        /* "Press Enter to apply" を非表示にする (スッキリさせるため) */
        [data-testid="InputInstructions"] {{
            display: none !important;
        }}
        
        /* 3. ボタンのスタイル (通常ボタン & ダウンロードボタン) */
        .stButton > button, 
        [data-testid="stDownloadButton"] > button {{
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 1px solid #cbd5e1 !important;
            padding: 0.5rem 1rem !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s !important;
        }}
        .stButton > button:hover, 
        [data-testid="stDownloadButton"] > button:hover {{
            border-color: #3b82f6 !important;
            color: #3b82f6 !important;
            background-color: #eff6ff !important;
        }}
        /* -----------------------------------------------------------------
           7. Image Tab Modern Buttons (Icon Only - Leaf Column Targeting)
           ----------------------------------------------------------------- */
        /* Target ONLY the leaf columns (no nested columns) that contain our markers */
        
        /* Select Button */
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-select):not(:has(div[data-testid="stColumn"])) button {{
            background-color: transparent !important;
            background-image: url("{ICON_CIRCLE_CHECK_OUTLINE}") !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-size: 26px !important;
            border: none !important;
            width: 32px !important;
            height: 32px !important;
            min-width: 32px !important;
            min-height: 32px !important;
            padding: 0 !important;
            box-shadow: none !important;
            margin-top: -16px !important; /* Even higher */
        }}
        
        /* Selected State */
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-select.selected):not(:has(div[data-testid="stColumn"])) button {{
            background-image: url("{ICON_CIRCLE_CHECK_SOLID}") !important;
        }}
        
        /* Save Button */
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-save):not(:has(div[data-testid="stColumn"])) button {{
            background-color: transparent !important;
            background-image: url("{ICON_DOWNLOAD_TRAY}") !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-size: 24px !important;
            border: none !important;
            width: 32px !important;
            height: 32px !important;
            min-width: 32px !important;
            min-height: 32px !important;
            padding: 0 !important;
            box-shadow: none !important;
            margin-top: -16px !important; /* Even higher */
            margin-left: -18px !important; /* Even closer to Select icon */
        }}
        
        /* Hide all internal text/elements for these specific buttons */
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-select):not(:has(div[data-testid="stColumn"])) button *,
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-save):not(:has(div[data-testid="stColumn"])) button * {{
            display: none !important;
        }}
        
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-select):not(:has(div[data-testid="stColumn"])) button:hover,
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-save):not(:has(div[data-testid="stColumn"])) button:hover {{
            background-color: rgba(0,0,0,0.05) !important;
            border-radius: 4px !important;
        }}
        
        /* Dim icon for saved state */
        .stApp div[data-testid="stColumn"]:has(.img-btn-col-save.saved):not(:has(div[data-testid="stColumn"])) button {{
            opacity: 0.4 !important;
        }}
        /* ----------------------------------------------------------------- */
        /* ----------------------------------------------------------------- */

        /* 4. Obsolete Copy Button Style Removed (Using render_copy_header instead) */
        
        /* 選択ボタン (チェックボックス風) - 未選択状態 */
        .stButton > button[kind="secondary"]:has(> div > p:first-child) {{
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
            border: 2px solid #e2e8f0 !important;
            color: #64748b !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
        }}
        .stButton > button[kind="secondary"]:has(> div > p:first-child):hover {{
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
            border-color: #94a3b8 !important;
            color: #475569 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07) !important;
        }}
        
        /* 選択ボタン (チェックボックス風) - 選択状態 / ダウンロードボタン (Primary) */
        .stButton > button[kind="primary"],
        [data-testid="stDownloadButton"] > button[kind="primary"] {{
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
            border: 2px solid #2563eb !important;
            color: #ffffff !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35) !important;
        }}
        .stButton > button[kind="primary"]:hover,
        [data-testid="stDownloadButton"] > button[kind="primary"]:hover {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            border-color: #1d4ed8 !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.45) !important;
        }}
        .stButton > button[kind="primary"]:disabled,
        [data-testid="stDownloadButton"] > button[kind="primary"]:disabled {{
            background: #e2e8f0 !important;
            border-color: #cbd5e1 !important;
            color: #94a3b8 !important;
            cursor: not-allowed !important;
            box-shadow: none !important;
            transform: none !important;
            opacity: 0.8 !important;
        }}

        /* セレクトボックス (ドロップダウン) のスタイル - 目立たせる */
        [data-testid="stSelectbox"] > div > div {{
            background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%) !important;
            border: 2px solid #3b82f6 !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15) !important;
            transition: all 0.2s ease !important;
        }}
        [data-testid="stSelectbox"] > div > div:hover {{
            border-color: #2563eb !important;
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.25) !important;
            transform: translateY(-1px);
        }}
        /* セレクトボックスの矢印アイコンを目立たせる */
        [data-testid="stSelectbox"] svg {{
            color: #3b82f6 !important;
        }}
        
        /* 5. タブデザイン (幅を広げる) */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: #e2e8f0;
            padding: 6px;
            border-radius: 12px;
            margin-bottom: 2rem;
            display: flex; /* フレックスコンテナ化 */
        }}
        .stTabs [data-baseweb="tab"] {{
            flex: 1; /* 均等に広げる */
            background-color: transparent !important;
            color: #64748b !important;
            font-weight: 700 !important;
            border: none !important;
            justify-content: center; /* 文字中央揃え */
            white-space: nowrap;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #ffffff !important;
            color: #3b82f6 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        }}

        /* 6. レイアウト: Single Scroll Parent (単一スクロール) - 翻訳タブ専用 */
        .trans-unified-container {{
            height: 78vh; 
            border: 1px solid #e2e8f0; border-radius: 20px; 
            overflow: hidden; background: #ffffff !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.05);
            display: flex; flex-direction: column;
        }}
        .trans-unified-header {{ 
            display: flex;
            background: #f1f5f9 !important; 
            border-bottom: 1px solid #e2e8f0; 
            flex-shrink: 0; /* ヘッダーは縮まない */
        }}
        .trans-header-cell {{ 
            flex: 1;
            padding: 14px 24px; font-weight: 800; color: #475569 !important; 
            text-transform: uppercase; font-size: 0.8em;
            border-right: 1px solid #e2e8f0;
        }}
        
        /* スクロール領域 (全体を包む) - 翻訳タブ専用 */
        .trans-scroll-pane-wrapper {{
            flex: 1;
            overflow-y: auto; /* ここでスクロール */
            background: white !important;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
        }}
        .trans-scroll-pane-wrapper::-webkit-scrollbar {{ width: 6px; }}

        .trans-scroll-pane-wrapper::-webkit-scrollbar-thumb {{ background-color: #cbd5e1; border-radius: 3px; }}
        .trans-scroll-pane-wrapper::-webkit-scrollbar-track {{ background: transparent; }}

        /* Grid Container - 左右2列のレイアウト - 翻訳タブ専用 */
        .trans-grid-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            height: 100%;
            overflow: hidden;
        }}
        
        /* 各列（左右それぞれ独立したスクロール領域） - 翻訳タブ専用 */
        .trans-column-wrapper {{
            overflow-y: auto;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
            /* 選択範囲を列内に限定 */
            isolation: isolate;
        }}
        .trans-column-wrapper::-webkit-scrollbar {{ width: 6px; }}
        .trans-column-wrapper::-webkit-scrollbar-thumb {{ background-color: #cbd5e1; border-radius: 3px; }}
        .trans-column-wrapper::-webkit-scrollbar-track {{ background: transparent; }}

        .trans-paragraph-block {{
            padding: 24px 32px;
            line-height: 1.9;
            border-bottom: 1px solid #f1f5f9;
            box-sizing: border-box;
            transition: min-height 0.2s ease;
            margin-bottom: 0 !important;
            user-select: text;
            -webkit-user-select: text;
            -moz-user-select: text;
            -ms-user-select: text;
        }}
        
        /* テキスト選択時のスタイル - 白文字に */
        .trans-paragraph-block::selection {{
            background-color: #3b82f6;
            color: #ffffff;
        }}
        .trans-paragraph-block::-moz-selection {{
            background-color: #3b82f6;
            color: #ffffff;
        }}
        .trans-paragraph-block *::selection {{
            background-color: #3b82f6;
            color: #ffffff;
        }}
        .trans-paragraph-block *::-moz-selection {{
            background-color: #3b82f6;
            color: #ffffff;
        }}
        
        /* 右列のみ右ボーダー */
        .trans-column-wrapper:first-child .trans-paragraph-block {{
            border-right: 1px solid #f1f5f9;
        }}
        .trans-paragraph-block h3 {{ margin: 0 0 16px 0 !important; line-height: 1.4 !important; font-weight: 800 !important; }}
        
        .trans-engine-label {{ 
            font-size: 10px; color: #94a3b8; background: #f1f5f9; 
            padding: 3px 8px; border-radius: 6px; display: inline-block; margin-bottom: 8px; font-weight: 600;
        }}

        /* OCR Result Card Styles */
        .ocr-result-card {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}
        .ocr-label {{
            font-size: 0.75rem;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        .ocr-text {{
            font-size: 1rem;
            line-height: 1.6;
            color: #1e293b;
            margin-bottom: 12px;
            white-space: pre-wrap;
        }}
    </style>
    """, unsafe_allow_html=True)

    st.title("メディア記事 解析＆比較ツール")


    # --- Reset Button ---
    with st.container():
        # Use columns to align button to the right or just place it
        # Placing it simply below title for now, or maybe small button
        if st.button("リセット (新しい記事を解析)", type="secondary", key="reset_btn_v9"):
            # Clear all relevant keys
            keys_to_clear = [
                "s_url_v9", "c_url_v9", "src_in_v9", "cmp_in_v9",
                "detected_lang_url", "src_lang_select", "trans_engine_select", 
                "compare_engine_select", "show_comparison_view",
                "images_loaded_v9", "loaded_images_v9"
            ]
            # Also clear dynamic keys for translation and images
            all_keys = list(st.session_state.keys())
            for k in all_keys:
                if k in keys_to_clear or k.startswith("t_v9_") or k.startswith("t_ttl_v9_") or k.startswith("img_chk_v9_") or k.startswith("chk_v9_"):
                    del st.session_state[k]
            
            # Explicitly reset widget values to empty string
            st.session_state["src_in_v9"] = ""
            st.session_state["cmp_in_v9"] = ""
            
            # Reset sets
            if "sel_imgs" in st.session_state:
                st.session_state.sel_imgs = set()
                
            st.rerun()

    c1, c2 = st.columns(2)
    src_url = c1.text_input("元記事URL", value=st.session_state.get("s_url_v9", ""), key="src_in_v9")
    cmp_url = c2.text_input("比較用URL (任意)", value=st.session_state.get("c_url_v9", ""), key="cmp_in_v9")
    st.session_state.s_url_v9 = src_url
    st.session_state.c_url_v9 = cmp_url

    src_article = load_article_v9(src_url) if src_url else None
    cmp_article = load_article_v9(cmp_url) if cmp_url else None
    
    # ... (Language detection logic omitted for brevity as it's unchanged in this block) ...

    # セッション状態の初期化 (廃止: mainの冒頭に移動済み)

    tab_titles = ["原文抽出/翻訳", "画像読込", "文章比較"]
    tabs = st.tabs(tab_titles)

    # --- タブ1: 原文抽出/翻訳 ---
    with tabs[0]:
        if src_article:
            # 比較用URLが入力されていても、このタブでは翻訳機能のみを提供する
            # if cmp_article checks removed to keep translation view active
            t_key = f"t_v9_{src_url}"
            
            # URLが変更された場合、言語選択をリセットして自動判定を再実行させる
            if "last_src_url" not in st.session_state:
                st.session_state["last_src_url"] = ""
            
            if st.session_state["last_src_url"] != src_url:
                if "src_lang_select" in st.session_state:
                    del st.session_state["src_lang_select"]
                st.session_state["last_src_url"] = src_url
            
            # 言語マップ（共通で使用）
            lang_map = {
                "自動検出": "auto",
                "中国語 (簡体字)": "zh-CN",
                "中国語 (繁体字)": "zh-TW",
                "英語": "en"
            }
            
            # Change: Render Settings UI ALWAYS (not just when t_key is missing)
            # so that API info remains visible after translation.
            
            # 言語選択とDeepL API設定
            # Change: Equal width for DeepL and Gemini settings (Request: "same width")
            # col1: Language Select (Small)
            # col2: DeepL Settings (Medium)
            # col3: Gemini Settings (Medium - same as DeepL)
            lang_col1, lang_col2, lang_col3 = st.columns([1, 2, 2])
        
            # 自動判定: コンテンツから言語を推定してデフォルト設定
            if "src_lang_select" not in st.session_state:
                detected_code = detect_language(src_article.text[:2000] if src_article.text else "")
                
                # 判定ロジック
                is_english = detected_code.lower().startswith("en")
                is_chinese = detected_code.lower().startswith("zh") or detected_code == "mixed" # mixedも中国語扱い（または次でFallback）

                if is_english:
                        st.session_state["src_lang_select"] = "英語"
                elif "weixin.qq.com" in src_url:
                    # WeChat Special Handling
                    # "ja" -> False positive for Chinese (Kanji) -> Force Chinese
                    # "mixed" -> Likely Chinese with English UI elements -> Force Chinese
                    # "unknown" -> Fallback to Chinese
                    if detected_code.lower().startswith("ja") or detected_code == "mixed" or detected_code == "unknown":
                        st.session_state["src_lang_select"] = "中国語 (簡体字)"
                    elif is_chinese:
                        # Explicit Chinese
                        if "tw" in detected_code.lower() or "hant" in detected_code.lower():
                            st.session_state["src_lang_select"] = "中国語 (繁体字)"
                        else:
                            st.session_state["src_lang_select"] = "中国語 (簡体字)"
                    else:
                        # Other (e.g. fr, es, or specific code) -> Auto
                        st.session_state["src_lang_select"] = "自動検出"
                elif is_chinese:
                    if "tw" in detected_code.lower() or "hant" in detected_code.lower():
                        st.session_state["src_lang_select"] = "中国語 (繁体字)"
                    else:
                        st.session_state["src_lang_select"] = "中国語 (簡体字)"
                else:
                    st.session_state["src_lang_select"] = "自動検出"

            # 3. 言語選択UI (ラジオボタン)
            # session_stateにあればそれをindexとして使う
            lang_options = ["自動検出", "中国語 (簡体字)", "中国語 (繁体字)", "英語"]
            current_selection = st.session_state.get("src_lang_select", "自動検出")
            if current_selection not in lang_options:
                current_selection = "自動検出"
            
            default_index = lang_options.index(current_selection)

            with lang_col1:
                st.markdown("##### 元記事の言語")
                lang_choice_label = st.radio(
                    "元記事の言語",
                    lang_options,
                    index=default_index,
                    key="src_lang_select_radio",
                    label_visibility="collapsed",
                    horizontal=True
                )
                # Radioの変更をsession_stateに反映（key指定しているので自動だが、明示的同期が必要な場合あり）
                if lang_choice_label != st.session_state.get("src_lang_select"):
                     st.session_state["src_lang_select"] = lang_choice_label
                     # 言語変更時に翻訳結果をクリアするか？
                     # ユーザー体験的にはクリアしたほうが自然だが、今回は維持する？
                     # 維持すると再翻訳ボタンが必要。
                     st.rerun()

                # DEBUG info for user verification (Temporary)
                if "detected_code" in locals():
                    st.markdown(f"<div style='font-size:0.7em; color:#cbd5e1; margin-top:-5px;'>Detected: {detected_code}</div>", unsafe_allow_html=True)
                
            # Check for cookie-stored API key on load -> Moved to global scope
            # pass
        
            # DeepL APIキー入力（折りたたみ形式）
            with lang_col2.expander("🔑 DeepL APIキー設定（任意）", expanded=False):
                    st.markdown("""
                        <div style="font-size: 0.85em; color: #64748b; margin-bottom: 10px;">
                            DeepLのAPIキーをお持ちの場合、入力すると翻訳エンジンに「DeepL」が追加されます。
                        <a href="https://www.deepl.com/pro-api" target="_blank">APIキーを取得</a>
                        <span style="margin: 0 5px; color: #cbd5e1;">|</span>
                        お持ちのAPIキー確認方法は<a href="https://www.deepl.com/ja/your-account/keys" target="_blank">こちら</a>
                        <br>
                        <span style="color: #22c55e; font-size: 0.9em;">
                            ※入力したキーはブラウザに保存され、次回以降も自動的に読み込まれます（30日間有効）。
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    deepl_key_input = st.text_input(
                        "DeepL APIキー",
                        value=st.session_state.get("deepl_api_key", ""),
                        type="password",
                        key="deepl_key_input",
                        placeholder="xxxx-xxxx-xxxx-xxxx"
                    )
                    
                    # 保存ボタン (入力値が現在の保存値と異なる場合のみ表示)
                    current_saved_key = st.session_state.get("deepl_api_key", "")
                    if deepl_key_input != current_saved_key:
                        if st.button("APIキーをブラウザに保存", key="save_deepl_key"):
                            st.session_state["deepl_api_key"] = deepl_key_input
                            
                            # Save to cookie for 30 days
                            expires = datetime.datetime.now() + datetime.timedelta(days=30)
                            cookie_manager.set("deepl_api_key_cookie", deepl_key_input, expires_at=expires)
                            
                            # 保存時はキャッシュクリアして再取得させる
                            if "deepl_usage_cache" in st.session_state:
                                del st.session_state["deepl_usage_cache"]
                            
                            st.session_state["deepl_key_saved_success"] = True
                            import time
                            time.sleep(0.5) # Wait for cookie to be set before rerun
                            st.rerun()
                    else:
                        # If key is saved and unchanged, show nothing or just text
                        if current_saved_key:
                            # Redundant message removed (handled by render_deepl_usage_ui)
                            pass
                    
                    # Revert: Show status and usage INSIDE the expander as requested by user
                    # Use explicit placeholders to try to manage state better
                    message_placeholder = st.empty()
                    usage_placeholder = st.empty()
                    
                    # 1. 保存/クリアのメッセージ表示
                    if st.session_state.get("deepl_key_saved_success", False):
                        with message_placeholder.container():
                            if st.session_state.get("deepl_api_key"):
                                st.success("✅ 保存済み")
                            else:
                                st.info("クリアしました")
                        del st.session_state["deepl_key_saved_success"]

                    # 2. 自動的に残量を確認・表示（キーがある場合）
                    saved_key = st.session_state.get("deepl_api_key")
                    if saved_key:
                        # Pass the placeholder directly
                        render_deepl_usage_ui(saved_key, usage_placeholder)
            
            # Gemini APIキー設定（折りたたみ形式）
            gemini_status_placeholder = None
            with lang_col3.expander("🧠 Gemini APIキー設定", expanded=False):
                st.markdown("""
                    <div style="font-size: 0.85em; color: #64748b; margin-bottom: 10px;">
                        Google AI StudioのAPIキーを入力すると「Gemini」が追加されます。<br>
                        (Free Tierで無料利用可能)
                    <a href="https://aistudio.google.com/app/apikey" target="_blank">APIキーを取得</a>
                    <br>
                    <span style="color: #22c55e; font-size: 0.9em;">
                        ※入力したキーはブラウザに保存され、次回以降も自動的に読み込まれます（30日間有効）。
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                gemini_key_input = st.text_input(
                    "Gemini APIキー",
                    value=st.session_state.get("gemini_api_key", ""),
                    type="password",
                    key="gemini_key_input",
                    placeholder="APIキーを入力してください (例: AIzaSy...)"
                )
                
                # Gemini保存ボタン (入力値が現在の保存値と異なる場合のみ表示)
                current_saved_gemini = st.session_state.get("gemini_api_key", "")
                if gemini_key_input != current_saved_gemini:
                    if st.button("Geminiキーをブラウザに保存", key="save_gemini_key"):
                        st.session_state["gemini_api_key"] = gemini_key_input
                        
                        # Save to cookie for 30 days
                        expires = datetime.datetime.now() + datetime.timedelta(days=30)
                        cookie_manager.set("gemini_v9_key", gemini_key_input, expires_at=expires)
                        
                        import time
                        time.sleep(0.5) # Wait for cookie to be set
                        
                        st.session_state["gemini_key_saved_success"] = True
                        st.rerun()
                else:
                    if st.session_state.get("gemini_api_key"):
                         # Fetch available models if not already in session state or explicitly requested
                         if "gemini_available_models" not in st.session_state:
                             try:
                                 with st.spinner("Geminiモデルリストを取得中..."):
                                    models = get_available_models(st.session_state["gemini_api_key"])
                                    # Filter for only gemini models
                                    gemini_models = [m.replace("models/", "") for m in models if "gemini" in m]
                                    # Sort: prioritized specific order (flash > pro, newer > older)
                                    # Simple heuristic: sort by length desc (usually more specific version) then alpha
                                    # But better to just sort alpha desc to get highest numbers first?
                                    # Actually, user wants "latest".
                                    gemini_models.sort(reverse=True) 
                                    st.session_state["gemini_available_models"] = gemini_models
                             except:
                                 st.session_state["gemini_available_models"] = ["gemini-2.5-flash", "gemini-1.5-pro"]

                         # Model Selection Dropdown
                         available_models = st.session_state.get("gemini_available_models", ["gemini-2.5-flash"])
                         
                         # Determine initial index from session state or cookie
                         saved_model = st.session_state.get("gemini_model_setting")
                         default_ix = 0
                         if saved_model in available_models:
                             default_ix = available_models.index(saved_model)
                         else:
                             # Fallback to gemini-2.5-flash if available
                             target_default = "gemini-2.5-flash"
                             if target_default in available_models:
                                 default_ix = available_models.index(target_default)
                         
                         selected_model = st.selectbox(
                             "使用するGeminiモデル", 
                             available_models, 
                             index=default_ix,
                             key="gemini_model_setting_widget",
                             help="通常は最新のFlashモデルが推奨されます。"
                         )
                         
                         # Sync selected model to global label and cookie immediately
                         if selected_model:
                             if selected_model != st.session_state.get("gemini_model_setting"):
                                 st.session_state["gemini_model_setting"] = selected_model
                                 # Update persistent cookie
                                 expires = datetime.datetime.now() + datetime.timedelta(days=30)
                                 cookie_manager.set("gemini_v9_model", selected_model, expires_at=expires)
                             
                             st.session_state["gemini_label_current"] = f"Gemini ({selected_model})"
                         
                         
                         
                         # Use a placeholder to prevent double rendering of usage/status
                         gemini_status_placeholder = st.empty()
                         
                         with gemini_status_placeholder.container():
                             st.markdown("""
                                <div style="
                                    margin-top: -15px; 
                                    margin-bottom: 10px;
                                    padding: 8px 12px; 
                                    background-color: #dcfce7; 
                                    color: #166534; 
                                    border-radius: 6px; 
                                    font-size: 0.9em; 
                                    font-weight: 600;
                                    border: 1px solid #bbf7d0;
                                    display: inline-flex;
                                    align-items: center;
                                    gap: 6px;
                                ">
                                    ✅ APIキーは保存されています
                                </div>
                            """, unsafe_allow_html=True)
                
                # Gemini Usage Display (Local Estimation)
                # API does not provide quota info, so we track locally.
                # Assuming Free Tier Limit: ~50 RPD (conservative estimate, officially "unspecified" or "variable")
                # User reported 20 RPD limit in error. Let's use 50 as visual max but warn at 20.
                
                # Load usage from cookie
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                usage_cookie = cookie_manager.get("gemini_usage_cookie")
                
                current_count = 0
                if usage_cookie:
                    try:
                        saved_date = usage_cookie.get("date")
                        saved_count = usage_cookie.get("count", 0)
                        if saved_date == today_str:
                            current_count = saved_count
                        else:
                            # New day, reset
                            current_count = 0
                    except:
                        current_count = 0
                
                # Display Progress
                limit = 50 # Visual limit
                usage_percent = min(current_count / limit, 1.0) * 100
                
                # Render usage inside the SAME placeholder container to group them
                if gemini_status_placeholder: # Ensure placeholder exists before using it
                    with gemini_status_placeholder.container():
                        st.markdown(f"""
                        <div style="margin-top: 10px; margin-bottom: 5px; font-weight: bold; font-size: 0.9em; color: #475569;">
                            本日使用回数 (推定): {current_count} 回
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Custom Progress Bar (Same style as DeepL)
                        bar_html = f"""
                        <div style="
                            background-color: #f1f5f9;
                            width: 100%;
                            height: 8px;
                            border-radius: 4px;
                            margin-top: 5px;
                            overflow: hidden;
                            margin-bottom: 10px;
                        ">
                            <div style="
                                background-color: #3b82f6;
                                width: {usage_percent}%;
                                height: 100%;
                                border-radius: 4px;
                                transition: width 0.5s ease;
                            "></div>
                        </div>
                        """
                        st.markdown(bar_html, unsafe_allow_html=True)
                        
                        st.markdown("""
                        <div style="font-size: 0.8em; color: #94a3b8; margin-bottom: 10px;">
                            ※ Gemini APIは正確な使用量を取得できないため、このアプリ内での実行回数をカウントしています。<br>
                            ※ 無料枠の上限は非公開ですが、1日50回程度が目安と言われています。
                        </div>
                        """, unsafe_allow_html=True)

                if st.session_state.get("gemini_key_saved_success", False):
                     st.success("✅ Geminiキーを保存しました")
                     del st.session_state["gemini_key_saved_success"]

            if 'lang_choice_label' not in locals():
                # Fallback or error handling
                # This should theoretically not happen if flow is correct, but avoids NameError
                lang_choice_label = "自動検出" 
            
            source_lang = lang_map[lang_choice_label]
            
            st.markdown("<br>", unsafe_allow_html=True)

            # Pre-Translation Placeholder Logic (Only show if NOT translated yet)
            if t_key not in st.session_state:
                st.markdown("""
                <style>
                    .pre-trans-block {
                        padding: 16px 20px;
                        border-bottom: 1px solid #f1f5f9;
                        line-height: 1.8;
                        color: #1e293b;
                        background-color: #ffffff;
                    }
                    .pre-trans-block h3 {
                        margin: 0 0 12px 0;
                        font-weight: 800;
                        line-height: 1.4;
                    }
                    .pre-trans-container {
                        border: 1px solid #e2e8f0;
                        border-radius: 0 0 12px 12px;
                        overflow: hidden;
                        background: #ffffff;
                    }
                    .pre-trans-placeholder {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100%;
                        min-height: 400px;
                        color: #94a3b8;
                        background-color: #f8fafc;
                        border: 2px dashed #e2e8f0;
                        border-radius: 0 0 12px 12px;
                        text-align: center;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                # --- Error Banner Display ---
                if st.session_state.get("v9_error_banner_html"):
                    st.markdown(st.session_state["v9_error_banner_html"], unsafe_allow_html=True)

                # ヘッダー行（3列：原文、翻訳1、比較翻訳）
                # 比較翻訳は初期状態では狭い
                hdr_col1, hdr_col2, hdr_col3 = st.columns([5, 5, 2])
                
                with hdr_col1:
                    full_orig_text = f"# {src_article.title}\n\n" + "\n\n".join([p["text"] for p in src_article.structured_html_parts]) if src_article else ""
                    render_copy_header("原文 (ORIGINAL)", full_orig_text, "orig_pre")
                
                with hdr_col2:
                    st.markdown("""
                    <div style="
                        background: #f1f5f9;
                        padding: 8px 16px;
                        border-radius: 10px 10px 0 0;
                        font-weight: 700;
                        color: #475569;
                        font-size: 0.75em;
                    ">翻訳 1</div>
                    """, unsafe_allow_html=True)
                    
                    # エンジン選択ドロップダウン（選択時に翻訳開始）
                    # エンジン選択ドロップダウン（選択時に翻訳開始）
                    engines = ["-- 選択してください --", "Google", "MyMemory"]
                    if st.session_state.get("deepl_api_key"):
                        engines.insert(2, "DeepL")
                    if st.session_state.get("gemini_api_key"):
                        gemini_label = st.session_state.get("gemini_label_current", "Gemini (gemini-2.5-flash)")
                        engines.insert(3 if "DeepL" in engines else 2, gemini_label)
                    selected_engine = st.selectbox(
                        "翻訳エンジン",
                        engines,
                        index=0,
                        key="engine_select_initial",
                        label_visibility="collapsed"
                    )
                    
                    # --- Progress & Status Area (Moved to Top) ---
                    st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
                    status_area_top = st.empty()
                    progress_area_top = st.empty()

                    st.markdown("<div style='margin-bottom: -40px;'></div>", unsafe_allow_html=True)
                    
                    # エンジンが選択されたら翻訳を実行
                    if selected_engine != "-- 選択してください --":
                        if not src_article.structured_html_parts:
                            st.error("本文が抽出されていないため、翻訳を実行できません。")
                        else:
                            # Defer translation execution to after grid rendering
                            st.session_state["run_translation_1"] = True
                            st.session_state["pending_engine_1"] = selected_engine
                            st.session_state["pending_model_1"] = st.session_state.get("gemini_model_setting", "gemini-2.5-flash")
                            
                            # Note: Title translation is also deferred/handled at the end now to assume consistent state
                            # But we need to ensure the title key is set if we want it to persist?
                            # The deferred block handles it.
                            
                            if "Gemini" in selected_engine:
                                # Load current
                                today_str = datetime.date.today().strftime("%Y-%m-%d")
                                usage_cookie = cookie_manager.get("gemini_usage_cookie")
                                current_count = 0
                                if usage_cookie:
                                    try:
                                        if usage_cookie.get("date") == today_str:
                                            current_count = usage_cookie.get("count", 0)
                                    except:
                                        pass
                                
                                # Increment
                                new_count = current_count + 1
                                new_cookie = {"date": today_str, "count": new_count}
                                
                                # Set cookie
                                expires = datetime.datetime.now() + datetime.timedelta(days=2)
                                cookie_manager.set("gemini_usage_cookie", new_cookie, expires_at=expires)
                        
                        # REMOVED st.rerun() to allow script to proceed to deferred execution block
                
                with hdr_col3:
                    st.markdown("""
                    <div style="
                        background: #f8fafc;
                        padding: 8px 12px;
                        border-radius: 10px 10px 0 0;
                        font-weight: 700;
                        color: #94a3b8;
                        font-size: 0.7em;
                        text-align: center;
                    ">比較翻訳</div>
                    """, unsafe_allow_html=True)
                
                # Initialize placeholders for deferred execution
                t1_placeholders = None
                t2_placeholders = None

                # 3列コンテンツエリア（比較翻訳は狭い）
                pc1, pc2, pc3 = st.columns([5, 5, 2])
                
                with pc1:
                    # 原文コンテンツの構築
                    content_html = f"<div class='pre-trans-container'>"
                    
                    # タイトル
                    l_title = f"<h3>{src_article.title}</h3><span style='font-size:0.8em; color:#64748b;'>{src_article.publisher}</span>"
                    content_html += f"<div class='pre-trans-block'>{l_title}</div>"
                    
                    # 本文
                    for i, p in enumerate(src_article.structured_html_parts):
                        l_content = f"<{p['tag']}>{p['text']}</{p['tag']}>"
                        content_html += f"<div class='pre-trans-block'>{l_content}</div>"
                    
                    content_html += "</div>"
                    st.markdown(content_html, unsafe_allow_html=True)
                    
                with pc2:
                    # 翻訳1プレースホルダー
                    # If translating, prepare the placeholder
                    if st.session_state.get("run_translation_1"):
                        t1_placeholders = st.empty()
                    else:
                        st.markdown("""
                        <div class="pre-trans-placeholder">
                            <div>
                                <div style="font-size: 2.5em; margin-bottom: 1rem; opacity: 0.5;">🌐</div>
                                <div style="font-weight:600;">エンジンを選択</div>
                                <div style="font-size:0.85em; margin-top:0.5rem;">上のドロップダウンから<br>翻訳エンジンを選択</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with pc3:
                    # 比較翻訳プレースホルダー（狭いバージョン）
                    st.markdown("""
                    <div style="
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100%;
                        min-height: 400px;
                        color: #cbd5e1;
                        background-color: #f8fafc;
                        border: 1px dashed #e2e8f0;
                        border-radius: 0 0 12px 12px;
                        text-align: center;
                        font-size: 0.75em;
                    ">
                        <div style="padding: 8px;">
                            <div style="font-size: 1.5em; margin-bottom: 0.5rem;">➕</div>
                            <div>翻訳1完了後<br>選択可能</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                show_dual_view = False
            else:
                # settings_section_placeholder.empty() # Removed: Keep settings visible
                
                # JS injection removed as we want to keep the UI visible
                pass

                # 翻訳済みの場合
                # source_lang は共通のlang_mapから取得（すでに上で定義済み）
                current_lang_label = st.session_state.get("src_lang_select", "自動検出")
                source_lang = lang_map.get(current_lang_label, "auto")

                # Check if comparison data exists
                t_key_2 = f"t_v9_{src_url}_2"
                trans_data = st.session_state[t_key]
                trans_data_2 = st.session_state.get(t_key_2, None)
                
                r_title = st.session_state[f"t_ttl_v9_{src_url}"]
                # r_headerは使わず、後続の構築ロジックで可変にする
                is_trans = True
                show_dual_view = True
                is_compare_mode = (trans_data_2 is not None)

            if show_dual_view:
                # HTMLブロックの構築 (Grid Layout)
                
                left_blocks = ""
                center_blocks = "" # Trans 1
                right_blocks = ""  # Trans 2 (optional)
                
                # --- Header with Engine Selectors (Streamlit Components) ---
                # Get current engine names from translation data
                engine_1 = ""
                engine_2 = ""
                if is_trans and trans_data and len(trans_data) > 0:
                    engine_1 = trans_data[0].get('engine', 'Google') if isinstance(trans_data[0], dict) else 'Google'
                    # Clean up fallback text
                    if "Fallback" in engine_1:
                        engine_1 = engine_1.split(" ")[0]
                if is_compare_mode and trans_data_2 and len(trans_data_2) > 0:
                    engine_2 = trans_data_2[0].get('engine', 'MyMemory')
                    if "Fallback" in engine_2:
                        engine_2 = engine_2.split(" ")[0]
                
                # Streamlit Header Row with Selectors
                # 比較モードでは三等分、そうでなければ比較列は狭い
                if is_compare_mode:
                    hdr_col1, hdr_col2, hdr_col3 = st.columns(3)
                else:
                    hdr_col1, hdr_col2, hdr_col3 = st.columns([4, 4, 4])
                
                with hdr_col1:
                    # Use unified header
                    full_orig_text = f"# {src_article.title}\n\n" + "\n\n".join([p["text"] for p in src_article.structured_html_parts])
                    render_copy_header("原文 (ORIGINAL)", full_orig_text, "orig")
                
                # Further cleanup of duplicate columns if necessary
                # But let's just use the call correctly.
                
                with hdr_col2:
                    # Engine 1 Selector
                    engines = ["Google", "DeepL", "MyMemory"] if st.session_state.get("deepl_api_key") else ["Google", "MyMemory"]
                    if st.session_state.get("gemini_api_key"):
                        gemini_label = st.session_state.get("gemini_label_current", "Gemini (gemini-2.5-flash)")
                        engines.insert(3 if "DeepL" in engines else 2, gemini_label)
                    
                    # Fallback detection
                    is_fallback_1 = "Fallback" in engine_1 or "Failed" in engine_1
                    display_engine_1 = "Google" if "Google" in engine_1 else engine_1
                    if "DeepL" in engine_1:
                        display_engine_1 = "DeepL"
                    elif "MyMemory" in engine_1 and "Fallback" not in engine_1:
                        display_engine_1 = "MyMemory"
                    elif "Gemini" in engine_1:
                         display_engine_1 = st.session_state.get("gemini_label_current", "Gemini (gemini-2.5-flash)")
                    
                    
                    current_engine_1_idx = engines.index(display_engine_1) if display_engine_1 in engines else 0
                    
                    # Use unified header
                    trans_data_1 = st.session_state.get(t_key, [])
                    t1_title = st.session_state.get(f"t_ttl_v9_{src_url}", "")
                    full_trans_1 = f"# {t1_title}\n\n" + "\n\n".join([p["text"] for p in trans_data_1])
                    render_copy_header("翻訳 1", full_trans_1, "trans_1")
                    
                    st.markdown("<div style='margin-bottom: -90px;'></div>", unsafe_allow_html=True)
                    new_engine_1 = st.selectbox(
                        "翻訳エンジン 1",
                        engines,
                        index=current_engine_1_idx,
                        key="engine_select_1",
                        label_visibility="collapsed"
                    )
                    
                    if is_fallback_1:
                        if "Failed" in engine_1 and "Fallback" not in engine_1:
                            # 完全な失敗（フォールバックなし）
                            st.error(f"❌ エラー詳細: {engine_1}")
                        else:
                            # フォールバック発生
                            st.warning(f"⚠️ {st.session_state.get('engine_1_selected', 'Requested Engine')} でのエラーのため Google にフォールバックしました。")
                    
                    # Re-translate if engine changed
                    # 保存されている前回のエンジンと比較
                    prev_engine_1 = st.session_state.get("engine_1_selected", engine_1)
                    if new_engine_1 != prev_engine_1:
                        st.session_state["engine_1_selected"] = new_engine_1
                        # Clear old translation state and error banners
                        st.session_state["v9_error_banner_html"] = None
                        t_key = f"t_v9_{src_url}"
                        if t_key in st.session_state: del st.session_state[t_key]
                        t_ttl_key = f"t_ttl_v9_{src_url}"
                        if t_ttl_key in st.session_state: del st.session_state[t_ttl_key]
                        
                        # Defer translation execution
                # Deferred blocks moved to end of script
                # Translation 1 (Main) - MOVED
                # Translation 2 (Compare) - MOVED
                
                if is_compare_mode:
                    with hdr_col3:
                        # Engine 2 Selector
                        # Fallback detection
                        is_fallback_2 = "Fallback" in engine_2 or "Failed" in engine_2
                        display_engine_2 = "Google" if "Google" in engine_2 else engine_2
                        if "DeepL" in engine_2:
                            display_engine_2 = "DeepL"
                        elif "MyMemory" in engine_2 and "Fallback" not in engine_2:
                            display_engine_2 = "MyMemory"
                        elif "Gemini" in engine_2:
                            display_engine_2 = st.session_state.get("gemini_label_current", "Gemini (gemini-2.5-flash)")
                            
                        current_engine_2_idx = engines.index(display_engine_2) if display_engine_2 in engines else 1
                        
                        # Use unified header
                        t_key_2 = f"t_v9_{src_url}_2"
                        trans_data_2 = st.session_state.get(t_key_2, [])
                        t2_text_parts = [p.get("text", "") for p in trans_data_2]
                        t2_title = st.session_state.get(f"t_ttl_v9_{src_url}_2", "")
                        full_trans_2 = f"# {t2_title}\n\n" + "\n\n".join(t2_text_parts)
                        render_copy_header("翻訳 2 (比較)", full_trans_2, "trans_2")
                        
                        st.markdown("<div style='margin-bottom: -90px;'></div>", unsafe_allow_html=True)
                        new_engine_2 = st.selectbox(
                            "翻訳エンジン 2",
                            engines,
                            index=current_engine_2_idx,
                            key="engine_select_2",
                            label_visibility="collapsed"
                        )
                        
                        # --- Comparison Progress & Status Area (Moved to Top) ---
                        st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
                        status_area_top_2 = st.empty()
                        progress_area_top_2 = st.empty()
                        
                        if is_fallback_2:
                            if "Failed" in engine_2 and "Fallback" not in engine_2:
                                st.error(f"❌ エラー詳細: {engine_2}")
                            else:
                                st.warning(f"⚠️ {st.session_state.get('engine_2_selected', 'Requested Engine')} エラー → Google")
                        
                        # Re-translate if engine changed
                        # 保存されている前回のエンジンと比較
                        prev_engine_2 = st.session_state.get("engine_2_selected", engine_2)
                        if new_engine_2 != prev_engine_2:
                            if not src_article.structured_html_parts:
                                st.error("本文が抽出されていないため、翻訳を実行できません。")
                            else:
                                st.session_state["engine_2_selected"] = new_engine_2
                                # Clear old translation state and error banners
                                st.session_state["v9_error_banner_html"] = None
                                t_key_2 = f"t_v9_{src_url}_2"
                                if t_key_2 in st.session_state: del st.session_state[t_key_2]
                                t_ttl_key_2 = f"t_ttl_v9_{src_url}_2"
                                if t_ttl_key_2 in st.session_state: del st.session_state[t_ttl_key_2]
                                
                                # Defer translation execution
                                st.session_state["run_translation_2"] = True
                                st.session_state["pending_engine_2"] = new_engine_2
                                st.session_state["pending_model_2"] = st.session_state.get("gemini_model_setting", "gemini-2.5-flash")
                                # REMOVED st.rerun()
                        # 初期設定
                        if "engine_2_selected" not in st.session_state:
                            st.session_state["engine_2_selected"] = engine_2
                else:
                    # 比較モードでない場合：記事生成セクション
                    with hdr_col3:
                        gen_key = f"gen_article_{src_url}"
                        has_gemini_key = bool(st.session_state.get("gemini_api_key"))
                        
                        # Header
                        st.markdown("""
                        <div style="
                            display: flex;
                            align-items: center;
                            gap: 8px;
                            padding: 6px 12px;
                            border-radius: 10px 10px 0 0;
                            background: linear-gradient(135deg, #eff6ff, #f0f9ff);
                        ">
                            <span style="font-size: 1.2em;">✍️</span>
                            <div>
                                <div style="font-weight: 700; font-size: 0.85em; color: #1e40af;">Shenzhen Fan 記事生成</div>
                                <div style="font-size: 0.7em; color: #64748b;">原文からプロパガンダ表現を除去し再構成</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show existing result header or generate button
                        if gen_key in st.session_state and st.session_state[gen_key]:
                            generated_text = st.session_state[gen_key]
                            render_copy_header("生成された記事", generated_text, "gen_article")
                            if st.button("🔄 再生成", key="regenerate_article", disabled=not has_gemini_key, use_container_width=True):
                                del st.session_state[gen_key]
                                st.rerun()
                        else:
                            if not has_gemini_key:
                                st.warning("Gemini APIキーを設定してください")
                            
                            if st.button(
                                "✍️ 記事を生成する",
                                key="generate_article_btn",
                                type="primary",
                                disabled=not has_gemini_key,
                                use_container_width=True,
                            ):
                                # Defer article generation (same pattern as translation)
                                st.session_state["run_article_gen"] = True
                        
                        # Status/progress area for comparison (keep for potential future use)
                        status_area_top_2 = st.empty()
                        progress_area_top_2 = st.empty()
                
                # Empty header_html since we're using Streamlit components above
                header_html = ""

                # --- Gemini Fallback Logic ---
                # Fallback to gemini-2.5-flash which is available and likely stable.
                fallback_target_model = "gemini-2.5-flash"
                
                # Check Engine 1 for Errors
                if trans_data and any("Gemini (Error)" in str(item.get("engine", "")) for item in trans_data):
                     current_e1 = st.session_state.get("engine_1_selected", "")
                     # Only show if we are actually using Gemini (to avoid confusion)
                     if "Gemini" in current_e1:
                         st.warning(f"⚠️ Geminiでの翻訳に失敗しました。")
                         if st.button(f"モデルを変更して再試行 ({fallback_target_model})", key="fallback_btn_1", help="より安定したモデルで再試行します"):
                             new_label = f"Gemini ({fallback_target_model})"
                             st.session_state["gemini_label_current"] = new_label
                             st.session_state["engine_1_selected"] = new_label
                             
                             # Execute translation immediately
                             with st.spinner(f"{new_label} で再試行中..."):
                                 st.session_state[t_key] = translate_paragraphs(
                                     src_article.structured_html_parts,
                                     engine_name=f"Gemini:{fallback_target_model}",
                                     source_lang=source_lang,
                                     deepl_api_key=st.session_state.get("deepl_api_key"),
                                     gemini_api_key=st.session_state.get("gemini_api_key")
                                 )
                                 st.session_state[f"t_ttl_v9_{src_url}"] = translate_paragraphs(
                                     [{"tag": "h1", "text": src_article.title}],
                                     engine_name=f"Gemini:{fallback_target_model}",
                                     source_lang=source_lang,
                                     deepl_api_key=st.session_state.get("deepl_api_key"),
                                     gemini_api_key=st.session_state.get("gemini_api_key")
                                 )[0]["text"]
                             st.rerun()

                # Check Engine 2 for Errors (Compare Mode)
                if is_compare_mode and trans_data_2 and any("Gemini (Error)" in str(item.get("engine", "")) for item in trans_data_2):
                     current_e2 = st.session_state.get("engine_2_selected", "")
                     if "Gemini" in current_e2:
                         st.warning(f"⚠️ Geminiでの翻訳に失敗しました (比較)。")
                         if st.button(f"モデルを変更して再試行 ({fallback_target_model})", key="fallback_btn_2", help="より安定したモデルで再試行します"):
                             new_label = f"Gemini ({fallback_target_model})"
                             st.session_state["gemini_label_current"] = new_label
                             st.session_state["engine_2_selected"] = new_label
                             
                             # Execute translation immediately
                             with st.spinner(f"{new_label} で再試行中..."):
                                 t_key_2 = f"t_v9_{src_url}_compare"
                                 st.session_state[t_key_2] = translate_paragraphs(
                                     src_article.structured_html_parts,
                                     engine_name=f"Gemini:{fallback_target_model}",
                                     source_lang=source_lang,
                                     deepl_api_key=st.session_state.get("deepl_api_key"),
                                     gemini_api_key=st.session_state.get("gemini_api_key")
                                 )
                                 st.session_state[f"t_ttl_v9_{src_url}_compare"] = translate_paragraphs(
                                     [{"tag": "h1", "text": src_article.title}],
                                     engine_name=f"Gemini:{fallback_target_model}",
                                     source_lang=source_lang,
                                     deepl_api_key=st.session_state.get("deepl_api_key"),
                                     gemini_api_key=st.session_state.get("gemini_api_key")
                                 )[0]["text"]
                             st.rerun()

                # --- Body Generation ---
                # Normalize length
                # Handle cases: 
                # 1. Trans Mode (Source, Trans1, [Trans2])
                # 2. Compare Article Mode (Source, CompareArticle) -> Mapped to Trans1 in previous step
                
                len_src = len(src_article.structured_html_parts)
                len_t1 = len(trans_data) if trans_data else 0
                len_t2 = len(trans_data_2) if trans_data_2 else 0
                max_len = max(len_src, len_t1, len_t2)
                
                # --- 3. Native Streamlit Layout (Grid Loop) ---
                # To support real-time streaming into individual paragraphs, we use st.columns in a loop.
                
                # Title Row
                # ----------------
                # Comparison mode layout or standard layout
                if is_compare_mode:
                    cols = st.columns(3)
                else:
                    cols = st.columns([4, 4, 4])
                
                # Title Styling
                title_style = """
                <div style="padding: 24px 32px; border-bottom: 2px solid #e2e8f0; margin-bottom: 10px; background: #fff;">
                    <h3 style="margin: 0; color: #1e293b; font-size: 1.4em;">{title}</h3>
                    {publisher_html}
                </div>
                    adjustToViewport();
                }});
                
                setTimeout(() => {{
                    syncRowHeights();
                    adjustToViewport();
                }}, 100);
                setTimeout(syncRowHeights, 500);
    </body>
    </html>
    """
                # Render content with Native Streamlit Grid (Row-by-Row)
                # ... (rest of the rendering code)

                # --- JS Injection for Alignment (Robust Method) ---
                # We use st.components.v1.html to inject a script that can access the parent DOM.
                # This is necessary because st.markdown scripts are often sandboxed or run too early.
                import streamlit.components.v1 as components
    
                js_alignment_script = """
                <script>
                    function syncRowHeights() {
                        try {
                            // Access the main Streamlit document
                            const doc = window.parent.document;
                            const blocks = doc.querySelectorAll('.trans-paragraph-block');
                
                            if (blocks.length === 0) return;
                
                            const rows = {};
                
                            // Group by index suffix (e.g., p-src-0, p-trans-0)
                            blocks.forEach(block => {
                                const id = block.id;
                                if (!id) return;
                                const parts = id.split('-');
                                const index = parts[parts.length - 1];
                                if (!rows[index]) rows[index] = [];
                                rows[index].push(block);
                            });
                
                            // Sync heights
                            Object.keys(rows).forEach(key => {
                                const rowBlocks = rows[key];
                                // Reset to auto to recalculate
                                rowBlocks.forEach(b => b.style.minHeight = 'auto');
                    
                                let maxHeight = 0;
                                rowBlocks.forEach(b => {
                                    if (b.offsetHeight > maxHeight) maxHeight = b.offsetHeight;
                                });
                    
                                // Apply max height
                                if (maxHeight > 0) {
                                    rowBlocks.forEach(b => {
                                        b.style.minHeight = maxHeight + 'px';
                                    });
                                }
                            });
                        } catch (e) {
                            console.error("SyncRowHeights Error:", e);
                        }
                    }

                    // Run periodically and on events
                    window.addEventListener('load', () => {
                        syncRowHeights();
                        setInterval(syncRowHeights, 500); // Check every 500ms for streaming updates
                    });
        
                    window.addEventListener('resize', syncRowHeights);
                </script>
                """
                components.html(js_alignment_script, height=0, width=0)
                # This restores the "formatted" look by aligning paragraphs and adding style.
                is_translating_1 = st.session_state.get("run_translation_1", False)
                is_translating_2 = st.session_state.get("run_translation_2", False)
    
                # Retrieve existing translations if available
                t1_title = st.session_state.get(f"t_ttl_v9_{src_url}", "")
                t2_title = st.session_state.get(f"t_ttl_v9_{src_url}_2", "")
    
                # Prepare lists for streaming placeholders
                if "t1_placeholders" not in locals() or not isinstance(t1_placeholders, list):
                    t1_placeholders = []
                if "t2_placeholders" not in locals() or not isinstance(t2_placeholders, list):
                    t2_placeholders = []
    
    
                # --- Title Row ---
                if is_compare_mode:
                    cols = st.columns(3)
                else:
                    cols = st.columns([5, 5, 2])
    
                # Original Title
                with cols[0]:
                    st.markdown(f"### {src_article.title}")
                    st.markdown(f"<span style='color:gray'>{src_article.publisher}</span>", unsafe_allow_html=True)
    
                # Trans 1 Title
                with cols[1]:
                    if is_translating_1:
                         # Placeholder for title? Or just skip
                        st.markdown("### 翻訳中...")
                    elif t1_title:
                        st.markdown(f"### {t1_title}")
    
                # Trans 2 Title / Control
                with cols[2]:
                    if is_compare_mode:
                        if is_translating_2:
                            st.markdown("### 翻訳中...")
                        elif t2_title:
                            st.markdown(f"### {t2_title}")
                    else:
                        # Generated article title
                        gen_key = f"gen_article_{src_url}"
                        if gen_key in st.session_state and st.session_state[gen_key]:
                            st.markdown("### ✍️ 生成記事")
                        else:
                            st.markdown("")

                st.markdown("---")


                # --- Paragraph Columns (Column-based Layout) ---
                # This isolates selection (user can select just original or just translation)
                # and removes the "card" look for a continuous flow.
    
                if is_compare_mode:
                    row_cols = st.columns(3)
                else:
                    row_cols = st.columns([4, 4, 4])
    
                # 1. Original Text Column
                with row_cols[0]:
                    for i, p in enumerate(src_article.structured_html_parts):
                        # Clean Text Style
                        st.markdown(f"""
                        <div id="p-src-{i}" class="trans-paragraph-block" style="
                            color: #334155;
                            font-size: 16px;
                            background-color: #ffffff;
                            padding: 16px;
                            border-radius: 8px;
                            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                            margin-bottom: 12px;
                        ">
                            {p['text']}
                        </div>
                        """, unsafe_allow_html=True)

                # 2. Translation 1 Column
                with row_cols[1]:
                    if is_translating_1:
                        # Create placeholders for each paragraph
                        for _ in src_article.structured_html_parts:
                            ph = st.empty()
                            t1_placeholders.append(ph)
                            # Initial loading state with correct spacing
                            ph.markdown(f"<div style='margin-bottom: 24px; color:#ccc'>...</div>", unsafe_allow_html=True)
                    else:
                        # Render existing translation
                        if trans_data:
                            for i, item in enumerate(trans_data):
                                t_text = item.get("text", "")
                                st.markdown(f"""
                                <div id="p-trans-{i}" class="trans-paragraph-block" style="
                                    color: #1e293b;
                                    font-size: 16px;
                                    background-color: #ffffff;
                                    padding: 16px;
                                    border-radius: 8px;
                                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                                    margin-bottom: 12px;
                                ">
                                    {t_text}
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                             # Empty state or mismatched length handling could go here
                             pass

                # 3. Translation 2 Column
                with row_cols[2]:
                    if is_compare_mode:
                        if is_translating_2:
                            for _ in src_article.structured_html_parts:
                                ph = st.empty()
                                t2_placeholders.append(ph)
                                ph.markdown(f"<div style='margin-bottom: 24px; color:#ccc'>...</div>", unsafe_allow_html=True)
                        else:
                            if trans_data_2:
                                for i, item in enumerate(trans_data_2):
                                    t_text_2 = item.get("text", "")
                                    st.markdown(f"""
                                    <div id="p-comp-{i}" class="trans-paragraph-block" style="
                                        color: #1e293b;
                                        font-size: 16px;
                                        background-color: #ffffff;
                                        padding: 16px;
                                        border-radius: 8px;
                                        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                                        margin-bottom: 12px;
                                    ">
                                        {t_text_2}
                                    </div>
                                    """, unsafe_allow_html=True)
                    else:
                        # Generated article content or placeholder
                        gen_key = f"gen_article_{src_url}"
                        if gen_key in st.session_state and st.session_state[gen_key]:
                            from src.article_generator import _format_article_html
                            generated_text = st.session_state[gen_key]
                            st.markdown(f"""
                            <div style="
                                color: #1e293b;
                                line-height: 2.0;
                                font-size: 15px;
                                padding: 20px 24px;
                                background: #ffffff;
                                border: 1px solid #e2e8f0;
                                border-radius: 12px;
                            ">{_format_article_html(generated_text)}</div>
                            """, unsafe_allow_html=True)
                        elif st.session_state.get("run_article_gen"):
                            # Placeholder while generating
                            gen_output_placeholder = st.empty()
                            gen_output_placeholder.markdown("""
                            <div style="
                                color: #64748b;
                                font-size: 0.9em;
                                padding: 40px 16px;
                                background: #f8fafc;
                                border: 1px solid #e2e8f0;
                                border-radius: 12px;
                                text-align: center;
                                min-height: 200px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                            ">
                                <div>
                                    <div style="font-size: 2em; margin-bottom: 12px;">⏳</div>
                                    <div>Geminiで記事を生成中...</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                            <div style="
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                min-height: 200px;
                                color: #94a3b8;
                                background: #f8fafc;
                                border: 1px dashed #e2e8f0;
                                border-radius: 12px;
                                text-align: center;
                                font-size: 0.85em;
                            ">
                                <div>
                                    <div style="font-size: 2em; margin-bottom: 8px;">✍️</div>
                                    <div>上の「記事を生成する」ボタン<br>をクリックして記事を生成</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

            else:
                st.info("元記事のURLを入力してください。")


    # --- Deferred Execution Blocks (Moved from inside columns) ---
    # These must be outside the conditionally rendered columns to ensure they always run if flagged.
    
    # Translation 1 (Main)
    if st.session_state.get("run_translation_1"):
        pending_engine = st.session_state.get("pending_engine_1")
        pending_model = st.session_state.get("pending_model_1")
        
        # Remove flags immediately to prevent re-run loop
        st.session_state["run_translation_1"] = False
        st.session_state["v9_error_banner_html"] = None
        
        with st.spinner(f"{pending_engine} で翻訳中..."):
            # Ensure placeholders exist
            # If t1_placeholders was populated in the loop above, use it.
            # If for some reason checking triggered without loop (unlikely), fallback.
            if "t1_placeholders" not in locals() or not t1_placeholders:
                # If we have no placeholders (e.g. empty details), we can't stream properly row-by-row.
                # Fallback to single area (legacy safely)
                t1_placeholders = st.empty()
            
            # Execute translation
            t_key = f"t_v9_{src_url}"
            st.session_state[t_key] = translate_paragraphs(
                src_article.structured_html_parts,
                engine_name=pending_engine,
                source_lang=source_lang,
                deepl_api_key=st.session_state.get("deepl_api_key"),
                gemini_api_key=st.session_state.get("gemini_api_key"),
                output_placeholder=t1_placeholders, 
                progress_placeholder=progress_area_top if 'progress_area_top' in locals() else None, 
                status_placeholder=status_area_top if 'status_area_top' in locals() else None,
                model_name=pending_model,
                item_id_prefix="p-trans"
            )
            
            # Title translation
            st.session_state[f"t_ttl_v9_{src_url}"] = translate_paragraphs(
                [{"tag": "h1", "text": src_article.title}],
                engine_name=pending_engine,
                source_lang=source_lang,
                deepl_api_key=st.session_state.get("deepl_api_key"),
                gemini_api_key=st.session_state.get("gemini_api_key")
            )[0]["text"]
            
        st.rerun()

    # Translation 2 (Compare)
    if st.session_state.get("run_translation_2"):
        pending_engine = st.session_state.get("pending_engine_2")
        pending_model = st.session_state.get("pending_model_2")
        
        st.session_state["run_translation_2"] = False
        st.session_state["v9_error_banner_html"] = None
        
        with st.spinner(f"{pending_engine} で比較翻訳中..."):
            if "t2_placeholders" not in locals() or not t2_placeholders:
                t2_placeholders = st.empty()
            
            t_key_2 = f"t_v9_{src_url}_2"
            st.session_state[t_key_2] = translate_paragraphs(
                src_article.structured_html_parts,
                engine_name=pending_engine,
                source_lang=source_lang,
                deepl_api_key=st.session_state.get("deepl_api_key"),
                gemini_api_key=st.session_state.get("gemini_api_key"),
                output_placeholder=t2_placeholders,
                progress_placeholder=progress_area_top_2 if 'progress_area_top_2' in locals() else None, 
                status_placeholder=status_area_top_2 if 'status_area_top_2' in locals() else None,
                model_name=pending_model,
                item_id_prefix="p-comp"
            )
            
            st.session_state[f"t_ttl_v9_{src_url}_2"] = translate_paragraphs(
                [{"tag": "h1", "text": src_article.title}],
                engine_name=pending_engine,
                source_lang=source_lang,
                deepl_api_key=st.session_state.get("deepl_api_key"),
                gemini_api_key=st.session_state.get("gemini_api_key")
            )[0]["text"]
            
        st.rerun()

    # Article Generation (Deferred)
    if st.session_state.get("run_article_gen"):
        st.session_state["run_article_gen"] = False
        
        gen_key = f"gen_article_{src_url}"
        model_name = st.session_state.get("gemini_model_setting", "gemini-2.5-flash")
        
        # Use the placeholder if it exists, otherwise create one
        gen_placeholder = gen_output_placeholder if 'gen_output_placeholder' in locals() else st.empty()
        
        # Prepare source text
        chinese_text = "\n\n".join(
            [p["text"] for p in src_article.structured_html_parts]
        )
        
        # Generate article
        result = generate_article(
            chinese_text=chinese_text,
            gemini_api_key=st.session_state.get("gemini_api_key", ""),
            model_name=model_name,
            article_title=src_article.title if 'src_article' in locals() else "",
            publisher=src_article.publisher if 'src_article' in locals() else "",
            output_placeholder=gen_placeholder,
        )
        
        # Save to session state
        if result and not result.startswith("[エラー]"):
            st.session_state[gen_key] = result
        
        st.rerun()

    # --- タブ2: 画像読込 ---
    with tabs[1]:
        # 画像読込タブ専用のセッション状態キー
        images_loaded_key = "images_loaded_v9"
        loaded_images_key = "loaded_images_v9"
        
        # URLが入力されているか確認 (複数ソースからフォールバック取得)
        # 1. 直接変数 2. widgetのkey 3. セッション状態
        current_url = src_url or st.session_state.get("src_in_v9", "") or st.session_state.get("s_url_v9", "")
        
        if current_url:
            # 「画像読込」ボタンを表示
            col_load, col_empty = st.columns([2, 8])
            
            # 読込済みかどうかの判定
            last_loaded = st.session_state.get("last_loaded_url_v9", "")
            is_loaded_same_url = (current_url == last_loaded) and bool(st.session_state.get(images_loaded_key))
            
            with col_load:
                btn_text = "読み込み済み" if is_loaded_same_url else "画像を読み込む"
                if st.button(btn_text, key="load_images_btn", type="primary", use_container_width=True, disabled=is_loaded_same_url):
                    with st.spinner("記事から画像を読み込み中..."):
                        article = load_article_v9(current_url)
                        if article and article.image_urls:
                            st.session_state[images_loaded_key] = True
                            st.session_state["last_loaded_url_v9"] = current_url
                            st.session_state[loaded_images_key] = {
                                "urls": article.image_urls,
                                "src_url": current_url
                            }
                            st.rerun()
                        else:
                            st.error("画像を読み込めませんでした。URLを確認してください。")
            
            # 画像が読み込まれている場合は表示
            if st.session_state.get(images_loaded_key) and st.session_state.get(loaded_images_key):
                loaded_data = st.session_state[loaded_images_key]
                image_urls = loaded_data["urls"]
                base_url = loaded_data["src_url"]
                
                st.markdown("""
                <style>
                    /* ツールバーボタン群のコンパクト化 */
                    .toolbar-container .stButton > button {
                        padding: 8px 16px !important;
                        font-size: 0.85em !important;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                # ツールバー風レイアウト（よりコンパクトに）
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 12px 16px;
                    margin-bottom: 16px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.03);
                ">
                """, unsafe_allow_html=True)
                
                # 操作ボタン群（コンパクトなgap）
                col1, col2, col_ocr, col_sep, col3 = st.columns([1.2, 1.2, 1.8, 0.3, 2.3], gap="small")
                
                with col1:
                    if st.button("全選択", key="all_v9", use_container_width=True):
                        for i in range(len(image_urls)):
                            st.session_state[f"img_chk_v9_{i}"] = True
                            st.session_state[f"chk_v9_{i}"] = True
                            st.session_state.sel_imgs.add(i)
                        st.rerun()
                
                with col2:
                    if st.button("解除", key="none_v9", use_container_width=True):
                        for i in range(len(image_urls)):
                            st.session_state[f"img_chk_v9_{i}"] = False
                            st.session_state[f"chk_v9_{i}"] = False
                            st.session_state.sel_imgs.discard(i)
                        st.rerun()

                with col_ocr:
                    # Determine Gemini model
                    gemini_model = st.session_state.get("gemini_model_setting", "gemini-2.0-flash")
                    gemini_key = st.session_state.get("gemini_api_key")
                    
                    # 選択状態をウィジェットの状態から直接再計算
                    current_sel_indices = [
                        i for i in range(len(image_urls))
                        if st.session_state.get(f"chk_v9_{i}", False)
                    ]
                    
                    if st.button("OCR翻訳", key="ocr_btn_v9", use_container_width=True, type="primary", disabled=not (gemini_key and current_sel_indices)):
                        if not gemini_key:
                            st.error("Gemini APIキーを設定してください。")
                        else:
                            ocr_results = st.session_state.get("ocr_results_v9", {})
                            progress_text = st.empty()
                            progress_bar = st.progress(0)
                            
                            for idx, abs_idx in enumerate(current_sel_indices):
                                progress_text.text(f"画像 {idx+1}/{len(current_sel_indices)} を処理中...")
                                progress_bar.progress((idx + 1) / len(current_sel_indices))
                                
                                img_url = image_urls[abs_idx]
                                img_b64, _, _ = fetch_image_data_v10(img_url, base_url)
                                
                                if img_b64:
                                    try:
                                        mime_type = img_b64.split(";")[0].split(":")[1]
                                        b64_data = img_b64.split(",")[1]
                                        image_bytes = base64.b64decode(b64_data)
                                        
                                        res = ocr_and_translate_image(image_bytes, mime_type, gemini_key, gemini_model)
                                        if not res.get("error"):
                                            ocr_results[abs_idx] = res
                                        else:
                                            st.error(f"画像 {abs_idx+1} の処理中にエラーが発生しました: {res['error']}")
                                    except Exception as e:
                                        st.error(f"画像 {abs_idx+1} の解析に失敗しました: {e}")
                            
                            st.session_state["ocr_results_v9"] = ocr_results
                            progress_text.empty()
                            progress_bar.empty()
                            st.rerun()

                with col_sep:
                    # 区切り線的なスペース
                    st.markdown("<div style='border-left: 2px solid #e2e8f0; height: 38px; margin: 0 auto;'></div>", unsafe_allow_html=True)
                
                with col3:
                    # 選択状態をウィジェットの状態から直接再計算
                    current_sel_indices = [
                        i for i in range(len(image_urls))
                        if st.session_state.get(f"chk_v9_{i}", False)
                    ]
                    target_urls = [image_urls[i] for i in current_sel_indices]
                    sel_count = len(current_sel_indices)
                    
                    st.session_state.sel_imgs = set(current_sel_indices)
                    
                    if sel_count == 1:
                        # 1枚のみ選択: 直接ダウンロード
                        single_url = target_urls[0]
                        single_idx = current_sel_indices[0]
                        img_b64_single, _, img_fmt_single = fetch_image_data_v10(single_url, base_url)
                        if img_b64_single:
                            # Simplified: use global base64
                            try:
                                b64_data = img_b64_single.split(",", 1)[1]
                                img_bytes_single = base64.b64decode(b64_data)
                                ext = (img_fmt_single or "jpg").lower()
                                if ext == "jpeg": ext = "jpg"
                                st.download_button(
                                    label=f"ダウンロード (1枚)",
                                    data=img_bytes_single,
                                    file_name=f"image_{single_idx + 1}.{ext}",
                                    mime=f"image/{img_fmt_single.lower() if img_fmt_single else 'jpeg'}",
                                    key="dl_btn_single_v9",
                                    use_container_width=True,
                                    type="primary"
                                )
                            except:
                                st.button("ダウンロード (1枚)", disabled=True, use_container_width=True)
                        else:
                            st.button("ダウンロード (1枚)", disabled=True, use_container_width=True)
                    elif sel_count > 1:
                        # 2枚以上: ZIP形式でダウンロード
                        zip_bytes = create_images_zip(target_urls, base_url)
                        if zip_bytes:
                            st.download_button(
                                label=f"ダウンロード ({sel_count}枚)",
                                data=zip_bytes,
                                file_name="images.zip",
                                mime="application/zip",
                                key="dl_btn_v9",
                                use_container_width=True,
                                type="primary"
                            )
                    else:
                        st.markdown("""
                        <div style="
                            padding: 0.5rem 1rem;
                            min-height: 38px;
                            border: 1px dashed #94a3b8;
                            border-radius: 8px;
                            background-color: #ffffff;
                            color: #64748b;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 0.9em;
                            font-weight: 600;
                            box-sizing: border-box;
                        ">
                            画像を選択してください
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 画像グリッド表示（4列）
                cols_per_row = 4
                for i in range(0, len(image_urls), cols_per_row):
                    row_urls = image_urls[i:i + cols_per_row]
                    cols = st.columns(cols_per_row, gap="medium")
                    
                    for j, img_url in enumerate(row_urls):
                        abs_idx = i + j
                        with cols[j]:
                            # Card-like container
                            with st.container(border=True):
                                # 1. State Check
                                is_selected = abs_idx in st.session_state.sel_imgs

                                # 2. Prepare Image & Dims & Format
                                img_b64, img_dims, img_fmt = fetch_image_data_v10(img_url, base_url)
                                
                                # 3. Header Row: Select Button | Save Button | Dims/Format
                                h_c1, h_c2, h_c3 = st.columns([1.2, 1.2, 7.6])
                                
                                with h_c1:
                                    # Marker for Select column
                                    marker_class = "img-btn-col-select selected" if is_selected else "img-btn-col-select"
                                    st.markdown(f'<div class="{marker_class}" style="display:none"></div>', unsafe_allow_html=True)
                                    
                                    if st.button("\u200b", key=f"btn_card_{abs_idx}", help="選択/解除"):
                                        if is_selected:
                                            st.session_state.sel_imgs.discard(abs_idx)
                                            st.session_state[f"img_chk_v9_{abs_idx}"] = False
                                            st.session_state[f"chk_v9_{abs_idx}"] = False
                                        else:
                                            st.session_state.sel_imgs.add(abs_idx)
                                            st.session_state[f"img_chk_v9_{abs_idx}"] = True
                                            st.session_state[f"chk_v9_{abs_idx}"] = True
                                        st.rerun()

                                with h_c2:
                                    # Save (Download) Button - Individual Download
                                    saved_key = f"saved_v9_{abs_idx}"
                                    is_saved = st.session_state.get(saved_key, False)
                                    
                                    if is_saved:
                                        # Already saved - show completed state (same height as button)
                                        # Already saved - show as icon marker (will be dimmed by CSS)
                                        st.markdown('<div class="img-btn-col-save saved" style="display:none"></div>', unsafe_allow_html=True)
                                        st.button("\u200b", key=f"saved_btn_{abs_idx}", disabled=True, help="保存済み")
                                    elif img_b64:
                                        # Not saved yet - show download button
                                        # Simplified: use global base64
                                        try:
                                            b64_data = img_b64.split(",", 1)[1]
                                            img_bytes = base64.b64decode(b64_data)
                                            ext = img_fmt.lower() if img_fmt else "jpg"
                                            if ext == "jpeg":
                                                ext = "jpg"
                                            
                                            # Use on_click to set state BEFORE the download triggers
                                            def mark_saved(key):
                                                st.session_state[key] = True
                                            
                                            # Marker for Save column
                                            st.markdown('<div class="img-btn-col-save" style="display:none"></div>', unsafe_allow_html=True)
                                            st.download_button(
                                                label="\u200b",
                                                data=img_bytes,
                                                file_name=f"image_{abs_idx + 1}.{ext}",
                                                mime=f"image/{img_fmt.lower() if img_fmt else 'jpeg'}",
                                                key=f"dl_single_{abs_idx}",
                                                help="ダウンロード (保存)",
                                                on_click=mark_saved,
                                                args=(saved_key,)
                                            )
                                        except:
                                            st.button("保存", key=f"dl_err_{abs_idx}", disabled=True, use_container_width=True)
                                    else:
                                        # No image available
                                        st.button("保存", key=f"dl_na_{abs_idx}", disabled=True, use_container_width=True)

                                with h_c3:
                                    # Dimensions & Format (Right Aligned)
                                    if img_dims:
                                        info_str = f"{img_dims} <span style='font-size:0.8em; color:#94a3b8; margin-left:4px;'>{img_fmt}</span>"
                                        st.markdown(f"""
                                        <div style="
                                            text-align: right; 
                                            color: #64748b; 
                                            font-weight: 700; 
                                            font-family: monospace;
                                            font-size: 1.15em;
                                            padding-top: 4px;
                                            padding-right: 2px;
                                            letter-spacing: 0.05em;
                                            white-space: nowrap;
                                        ">
                                        {info_str}
                                        </div>
                                        """, unsafe_allow_html=True)

                                
                                # 4. Image Display (with Checkerboard)
                                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                                if img_b64:
                                    # Checkerboard CSS
                                    checker_style = """
                                        background-color: #f8fafc;
                                        background-image: 
                                          linear-gradient(45deg, #e2e8f0 25%, transparent 25%), 
                                          linear-gradient(-45deg, #e2e8f0 25%, transparent 25%), 
                                          linear-gradient(45deg, transparent 75%, #e2e8f0 75%), 
                                          linear-gradient(-45deg, transparent 75%, #e2e8f0 75%);
                                        background-size: 20px 20px;
                                        background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
                                        width: 100%; 
                                        height: 200px;
                                        object-fit: contain;
                                        border-radius: 4px; 
                                        display: block;
                                        border: 1px solid #e2e8f0;
                                    """
                                    st.markdown(f"""
                                        <img src="{img_b64}" style="{checker_style}">
                                    """, unsafe_allow_html=True)
                                else:
                                    st.markdown('''
                                    <div style="border: 2px dashed #e2e8f0; border-radius: 8px; padding: 20px; 
                                                background: #f1f5f9; text-align: center; color: #94a3b8; height: 200px; display: flex; align-items: center; justify-content: center;">
                                        <div style="font-size: 1.5em;">❌</div>
                                    </div>
                                    ''', unsafe_allow_html=True)
                                
                                # 5. OCR Results Display
                                ocr_results = st.session_state.get("ocr_results_v9", {})
                                if abs_idx in ocr_results:
                                    res = ocr_results[abs_idx]
                                    st.markdown(f"""
                                    <div class="ocr-result-card" style="margin-top: 12px;">
                                        <div class="ocr-label">原文 ( transciption )</div>
                                        <div class="ocr-text">{res['original_text']}</div>
                                        <div style="border-top: 1px solid #f1f5f9; margin: 8px 0;"></div>
                                        <div class="ocr-label">翻訳 ( Japanese )</div>
                                        <div class="ocr-text" style="color: #2563eb; font-weight: 500;">{res['translated_text']}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
            else:
                # 画像がまだ読み込まれていない場合のメッセージ
                st.markdown("""
                <div style="text-align: center; padding: 60px 40px; background: #f0f9ff; border-radius: 16px; margin: 20px 0; border: 1px solid #bae6fd;">
                    <h3 style="color: #0369a1; margin-bottom: 12px;">「画像を読み込む」ボタンをクリックしてください</h3>
                    <p style="color: #0284c7;">上のボタンをクリックすると、記事内の画像が表示されます。</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            # URLが入力されていない場合
            st.markdown("""
            <div style="text-align: center; padding: 80px 40px; background: #f8fafc; border-radius: 16px; margin: 20px 0;">
                <div style="font-size: 4em; margin-bottom: 20px;">🖼️</div>
                <h3 style="color: #475569; margin-bottom: 16px;">画像を読み込むには</h3>
                <p style="color: #64748b; margin-bottom: 24px;">
                    画面上部の「元記事URL」欄に中国メディア記事のURLを入力してください。<br>
                    その後、このタブで「画像を読み込む」ボタンをクリックしてください。
                </p>
            </div>
            """, unsafe_allow_html=True)

    # --- タブ3: 文章比較 ---
    with tabs[2]:
        if not src_url:
            st.info("まずは「元記事URL」を入力してください。")
        elif not cmp_url:
            st.markdown("""
            <div style="text-align: center; padding: 60px 40px; background: #f8fafc; border-radius: 16px; margin: 20px 0; border: 1px dashed #cbd5e1;">
                <div style="font-size: 3em; margin-bottom: 16px;">⚖️</div>
                <h3 style="color: #64748b; margin-bottom: 12px;">比較用URLが入力されていません</h3>
                <p style="color: #94a3b8;">
                    画面上部の「比較用URL」欄にURLを入力すると、<br>元記事との文章比較機能が有効になります。
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Comparison Logic
            if src_article and cmp_article:
                diff_table, _ = make_diff_html(src_article.text, cmp_article.text)
                st.markdown(textwrap.dedent(f"""
                    <div class="trans-unified-container" style="height:75vh;">
                        <div class="trans-unified-header">
                            <div class="trans-header-cell">元記事 差分</div>
                            <div class="trans-header-cell">比較記事 差分</div>
                        </div>
                        <div class="trans-scroll-pane-wrapper">
                            {diff_table}
                        </div>
                    </div>
                """), unsafe_allow_html=True)
            else:
                st.error("記事の読み込みに失敗しました。")

if __name__ == "__main__":
    main()