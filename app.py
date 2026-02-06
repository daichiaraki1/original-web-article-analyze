import textwrap
import streamlit as st
import streamlit.components.v1 as components
from src.scraper import load_article_v9
from src.translator import translate_paragraphs
from src.utils import create_images_zip, fetch_image_data_v10, make_diff_html

# --- メイン UI ---
def main():
    st.set_page_config(layout="wide", page_title="中国メディア解析ツール")
    
    # セッション状態の初期化 (最上部)
    if "sel_imgs" not in st.session_state:
        st.session_state.sel_imgs = set()
    if "s_url_v9" not in st.session_state:
        st.session_state.s_url_v9 = ""
    if "c_url_v9" not in st.session_state:
        st.session_state.c_url_v9 = ""
    st.markdown("""
    <style>
        /* 1. 基本設定と白モードの徹底強制 */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
            background-color: #f8fafc !important;
            color: #1e293b !important;
        }

        /* 2. 入力欄: 徹底的に白固定 & フォーカス時のグレー防止 */
        input[type="text"], 
        [data-testid="stTextInput"] div,
        [data-baseweb="input"],
        [data-baseweb="base-input"] {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border-color: #cbd5e1 !important;
        }
        /* フォーカス時も白を維持 */
        [data-baseweb="base-input"]:focus-within {
            background-color: #ffffff !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
        }
        
        /* "Press Enter to apply" を非表示にする (スッキリさせるため) */
        [data-testid="InputInstructions"] {
            display: none !important;
        }
        
        /* 3. ボタンのスタイル (通常ボタン & ダウンロードボタン) */
        .stButton > button, 
        [data-testid="stDownloadButton"] > button {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 1px solid #cbd5e1 !important;
            padding: 0.5rem 1rem !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s !important;
        }
        .stButton > button:hover,
        [data-testid="stDownloadButton"] > button:hover {
            border-color: #3b82f6 !important;
            color: #3b82f6 !important;
            background-color: #f0f9ff !important;
        }


        
        /* 5. タブデザイン (幅を広げる) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #e2e8f0;
            padding: 6px;
            border-radius: 12px;
            margin-bottom: 2rem;
            display: flex; /* フレックスコンテナ化 */
        }
        .stTabs [data-baseweb="tab"] {
            flex: 1; /* 均等に広げる */
            background-color: transparent !important;
            color: #64748b !important;
            font-weight: 700 !important;
            border: none !important;
            justify-content: center; /* 文字中央揃え */
            white-space: nowrap;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important;
            color: #3b82f6 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        }

        /* 6. レイアウト: Single Scroll Parent (単一スクロール) - 翻訳タブ専用 */
        .trans-unified-container {
            height: 78vh; 
            border: 1px solid #e2e8f0; border-radius: 20px; 
            overflow: hidden; background: #ffffff !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.05);
            display: flex; flex-direction: column;
        }
        .trans-unified-header { 
            display: flex;
            background: #f1f5f9 !important; 
            border-bottom: 1px solid #e2e8f0; 
            flex-shrink: 0; /* ヘッダーは縮まない */
        }
        .trans-header-cell { 
            flex: 1;
            padding: 14px 24px; font-weight: 800; color: #475569 !important; 
            text-transform: uppercase; font-size: 0.8em;
            border-right: 1px solid #e2e8f0;
        }
        
        /* スクロール領域 (全体を包む) - 翻訳タブ専用 */
        .trans-scroll-pane-wrapper {
            flex: 1;
            overflow-y: auto; /* ここでスクロール */
            background: white !important;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
        }
        .trans-scroll-pane-wrapper::-webkit-scrollbar { width: 6px; }
        .trans-scroll-pane-wrapper::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 3px; }
        .trans-scroll-pane-wrapper::-webkit-scrollbar-track { background: transparent; }

        /* Grid Container - 左右2列のレイアウト - 翻訳タブ専用 */
        .trans-grid-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            height: 100%;
            overflow: hidden;
        }
        
        /* 各列（左右それぞれ独立したスクロール領域） - 翻訳タブ専用 */
        .trans-column-wrapper {
            overflow-y: auto;
            scrollbar-width: thin;
            scrollbar-color: #cbd5e1 transparent;
            /* 選択範囲を列内に限定 */
            isolation: isolate;
        }
        .trans-column-wrapper::-webkit-scrollbar { width: 6px; }
        .trans-column-wrapper::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 3px; }
        .trans-column-wrapper::-webkit-scrollbar-track { background: transparent; }

        .trans-paragraph-block {
            padding: 24px 32px;
            line-height: 1.9;
            border-bottom: 1px solid #f1f5f9;
            box-sizing: border-box;
            user-select: text;
            -webkit-user-select: text;
            -moz-user-select: text;
            -ms-user-select: text;
        }
        
        /* テキスト選択時のスタイル - 白文字に */
        .trans-paragraph-block::selection {
            background-color: #3b82f6;
            color: #ffffff;
        }
        .trans-paragraph-block::-moz-selection {
            background-color: #3b82f6;
            color: #ffffff;
        }
        .trans-paragraph-block *::selection {
            background-color: #3b82f6;
            color: #ffffff;
        }
        .trans-paragraph-block *::-moz-selection {
            background-color: #3b82f6;
            color: #ffffff;
        }
        
        /* 右列のみ右ボーダー */
        .trans-column-wrapper:first-child .trans-paragraph-block {
            border-right: 1px solid #f1f5f9;
        }
        .trans-paragraph-block h3 { margin: 0 0 16px 0 !important; line-height: 1.4 !important; font-weight: 800 !important; }
        
        .trans-engine-label { 
            font-size: 10px; color: #94a3b8; background: #f1f5f9; 
            padding: 3px 8px; border-radius: 6px; display: inline-block; margin-bottom: 8px; font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("中国メディア記事 解析＆比較ツール")


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
            
            # 翻訳がまだ実行されていない場合
            if t_key not in st.session_state:
                # 翻訳実行ボタンを最上部に配置
                
                # 翻訳実行ボタンとエンジン選択を配置
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown("<div style='margin-bottom: 5px; font-weight: bold; color: #475569;'>翻訳エンジンを選択</div>", unsafe_allow_html=True)
                    engine_choice = st.radio(
                        "翻訳エンジンを選択",
                        ["Google", "MyMemory"],
                        key="trans_engine_select",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    
                    st.markdown("<div style='margin-top: 10px; margin-bottom: 5px; font-weight: bold; color: #475569;'>元記事の言語</div>", unsafe_allow_html=True)
                    lang_map = {
                        "自動検出": "auto",
                        "中国語 (簡体字)": "zh-CN",
                        "中国語 (繁体字)": "zh-TW",
                        "英語": "en"
                    }
                    lang_choice_label = st.radio(
                        "元記事の言語",
                        list(lang_map.keys()),
                        key="src_lang_select",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    source_lang = lang_map[lang_choice_label]
                    
                    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
                    
                    if st.button("🌐 翻訳を実行", key="translate_btn", type="primary", use_container_width=True):
                        with st.spinner(f"{engine_choice} で翻訳中..."):
                            st.session_state[t_key] = translate_paragraphs(src_article.structured_html_parts, engine_name=engine_choice, source_lang=source_lang)
                            st.session_state[f"t_ttl_v9_{src_url}"] = translate_paragraphs([{"tag":"h1", "text":src_article.title}], engine_name=engine_choice, source_lang=source_lang)[0]["text"]
                        st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)
                
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
                        border-radius: 12px;
                        overflow: hidden;
                        background: #ffffff;
                    }
                    .pre-trans-header {
                        background: #f1f5f9;
                        padding: 12px 20px;
                        font-weight: 800;
                        color: #475569;
                        font-size: 0.8em;
                        border-bottom: 1px solid #e2e8f0;
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
                        border-radius: 12px;
                        text-align: center;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                # 左右カラムを作成 (左: 原文, 右: プレースホルダー)
                pc1, pc2 = st.columns(2)
                
                with pc1:
                    # 原文コンテンツの構築
                    content_html = f"<div class='pre-trans-container'><div class='pre-trans-header'>元記事 (原文)</div>"
                    
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
                    # 右側：翻訳待ちプレースホルダー
                    st.markdown("""
                    <div class="pre-trans-placeholder">
                        <div>
                            <div style="font-size: 3em; margin-bottom: 1rem;">📝</div>
                            <div style="font-weight:600;">翻訳を実行してください</div>
                            <div style="font-size:0.85em; margin-top:0.5rem;">上の「翻訳を実行」ボタンをクリックすると<br>ここに日本語訳が表示されます</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                show_dual_view = False
            else:
                # 翻訳済みの場合
                # Define source_lang from session state for comparison translation
                lang_map = {
                    "自動検出": "auto",
                    "中国語 (簡体字)": "zh-CN",
                    "中国語 (繁体字)": "zh-TW",
                    "英語": "en"
                }
                current_lang_label = st.session_state.get("src_lang_select", "自動検出")
                source_lang = lang_map.get(current_lang_label, "auto")

                # === Comparison UI & Processing ===
                st.divider()
                st.markdown("##### 🔍 翻訳結果の比較 (オプション)")
                
                c_eng_col, c_btn_col = st.columns([2, 2])
                with c_eng_col:
                    compare_engine = st.radio(
                        "比較するエンジン",
                        ["Google", "MyMemory"],
                        key="compare_engine_select",
                        horizontal=True
                    )
                with c_btn_col:
                    st.markdown("<div style='margin-top: 24px'></div>", unsafe_allow_html=True)
                    if st.button("➕ 比較用翻訳を追加実行", key="compare_btn"):
                            with st.spinner(f"{compare_engine} で比較用翻訳を実行中..."):
                                t_key_2 = f"t_v9_{src_url}_compare"
                                st.session_state[t_key_2] = translate_paragraphs(
                                    src_article.structured_html_parts, 
                                    engine_name=compare_engine, 
                                    source_lang=source_lang
                                )
                                # 比較用タイトル翻訳も保存
                                st.session_state[f"t_ttl_v9_{src_url}_compare"] = translate_paragraphs([{"tag":"h1", "text":src_article.title}], engine_name=compare_engine, source_lang=source_lang)[0]["text"]
                                # 比較モードフラグ
                                st.session_state["show_comparison_view"] = True
                                st.rerun()

                # Check if comparison data exists
                t_key_2 = f"t_v9_{src_url}_compare"
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
                
                # --- Header Generation ---
                # Default Headers
                h_left = "原文 (ORIGINAL)"
                h_center = "翻訳 1" if is_compare_mode else "日本語翻訳"
                h_right = "翻訳 2 (比較)" if is_compare_mode else ""
                
                # Update Trans 1 Header with engine name
                if is_trans and trans_data and len(trans_data) > 0:
                     eng1 = trans_data[0].get('engine', '') if isinstance(trans_data[0], dict) else ''
                     if eng1: h_center += f" ({eng1})"
                elif not is_trans:
                     h_center = "比較対象記事"

                # Update Trans 2 Header with engine name
                if is_compare_mode and trans_data_2 and len(trans_data_2) > 0:
                     eng2 = trans_data_2[0].get('engine', '')
                     if eng2: h_right += f" ({eng2})"

                header_html = f"""
                <div class="trans-unified-header">
                    <div class="trans-header-cell">{h_left}</div>
                    <div class="trans-header-cell">{h_center}</div>
                    {'<div class="trans-header-cell">' + h_right + '</div>' if is_compare_mode else ''}
                </div>
                """

                # --- Body Generation ---
                # Normalize length
                # Handle cases: 
                # 1. Trans Mode (Source, Trans1, [Trans2])
                # 2. Compare Article Mode (Source, CompareArticle) -> Mapped to Trans1 in previous step
                
                len_src = len(src_article.structured_html_parts)
                len_t1 = len(trans_data) if trans_data else 0
                len_t2 = len(trans_data_2) if trans_data_2 else 0
                max_len = max(len_src, len_t1, len_t2)
                
                # --- Title Row (Prepend before body) ---
                title_orig = src_article.title or ""
                title_trans = r_title if is_trans else ""
                # 比較用タイトル翻訳を取得
                title_trans_2 = st.session_state.get(f"t_ttl_v9_{src_url}_compare", "") if is_compare_mode else ""
                
                left_blocks += f"<div class='trans-paragraph-block trans-title-block' id='src-row-title'><h3>{title_orig}</h3><span style='font-size:0.8em; color:#64748b;'>{src_article.publisher or ''}</span></div>"
                center_blocks += f"<div class='trans-paragraph-block trans-title-block' id='trans1-row-title'><h3>{title_trans}</h3></div>"
                if is_compare_mode:
                    right_blocks += f"<div class='trans-paragraph-block trans-title-block' id='trans2-row-title'><h3>{title_trans_2}</h3></div>"
            
                for i in range(max_len):
                    row_id = f"row-{i}"
                    
                    # 1. Left (Source)
                    if i < len_src:
                        p = src_article.structured_html_parts[i]
                        l_content = f"<{p['tag']}>{p['text']}</{p['tag']}>"
                    else:
                        l_content = ""
                    
                    left_blocks += f"<div class='trans-paragraph-block' id='src-{row_id}'>{l_content}</div>"

                    # 2. Center (Trans 1 or Compare Article)
                    if i < len_t1:
                        p = trans_data[i]
                        t_tag = p.get('tag', 'p')
                        t_text = p.get('text', '')
                        c_content = f"<{t_tag}>{t_text}</{t_tag}>"
                    else:
                        c_content = ""
                    center_blocks += f"<div class='trans-paragraph-block' id='trans1-{row_id}'>{c_content}</div>"

                    # 3. Right (Trans 2)
                    if is_compare_mode:
                        if i < len_t2:
                            p = trans_data_2[i]
                            t_tag = p.get('tag', 'p')
                            t_text = p.get('text', '')
                            r_content = f"<{t_tag}>{t_text}</{t_tag}>"
                        else:
                            r_content = ""
                        right_blocks += f"<div class='trans-paragraph-block' id='trans2-{row_id}'>{r_content}</div>"

                # --- CSS Injection for Columns ---
                grid_cols = "1fr 1fr 1fr" if is_compare_mode else "1fr 1fr"
                extra_css = f"""
                <style>
                    .trans-grid-container {{ grid-template-columns: {grid_cols} !important; }}
                </style>
                """

                # 3. HTML Layout
                html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        {extra_css}
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{ height: 100%; overflow: hidden; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }}
        
            .trans-unified-container {{
                height: 100%;
                display: flex;
                flex-direction: column;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                overflow: hidden;
                background: #fff;
            }}
        
            .trans-unified-header {{
                display: flex;
                background: #f1f5f9;
                border-bottom: 1px solid #e2e8f0;
                flex-shrink: 0;
            }}
        
            .trans-header-cell {{
                flex: 1;
                padding: 14px 24px;
                font-weight: 800;
                color: #475569;
                text-transform: uppercase;
                text-align: center;
                border-right: 1px solid #e2e8f0;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }}
            .trans-header-cell:last-child {{ border-right: none; }}
        
            .trans-scroll-pane-wrapper {{
                flex: 1;
                overflow-y: auto;
                background: white;
            }}
        
            .trans-grid-container {{
                display: grid;
                /* grid-template-columns set via extra_css */
                min-height: 100%;
            }}
        
            .trans-column-wrapper {{
                border-right: 1px solid #f1f5f9;
            }}
            .trans-column-wrapper:last-child {{ border-right: none; }}
        
            .trans-paragraph-block {{
                padding: 24px 32px;
                line-height: 1.8;
                border-bottom: 1px solid #f1f5f9;
                font-size: 15px; color: #334155;
            }}
        </style>
    </head>
    
    <body>
        <div class="trans-unified-container unified-container">
            {header_html}
            
            <div class="trans-scroll-pane-wrapper">
                <div class="trans-grid-container">
                    <div class="trans-column-wrapper">
                        {left_blocks}
                    </div>
                    <div class="trans-column-wrapper">
                        {center_blocks}
                    </div>
                    {f'<div class="trans-column-wrapper">{right_blocks}</div>' if is_compare_mode else ''}
                </div>
            </div>
        </div>
        <script>
            (function() {{
                const syncRowHeights = () => {{
                    // 全ての src-row- で始まるIDを持つ要素を取得
                    const srcRows = document.querySelectorAll('[id^="src-row-"]');
                    if (srcRows.length === 0) {{
                        console.log('No src rows found');
                        return;
                    }}
                    console.log('Found ' + srcRows.length + ' src rows');

                    srcRows.forEach(srcEl => {{
                        const idStr = srcEl.id;
                        // src-row-X から X を取り出す (X は title, 0, 1, 2, ...)
                        const idx = idStr.substring(8); // 'src-row-' is 8 chars
                        const elSrc = document.getElementById('src-row-' + idx);
                        const elT1 = document.getElementById('trans1-row-' + idx);
                        const elT2 = document.getElementById('trans2-row-' + idx);
                        const elements = [elSrc, elT1, elT2].filter(el => el);
                        
                        // まず高さをリセット
                        elements.forEach(el => el.style.minHeight = 'auto');
                        
                        // 最大高さを計算
                        let maxHeight = 0;
                        elements.forEach(el => {{
                            const h = el.getBoundingClientRect().height;
                            if (h > maxHeight) maxHeight = h;
                        }});
                        
                        // 最大高さを適用
                        if (maxHeight > 0) {{
                            elements.forEach(el => el.style.minHeight = maxHeight + 'px');
                        }}
                    }});
                }};

                // Dynamic Height Sensing from Parent
                const adjustToViewport = () => {{
                    try {{
                        // Streamlit Cloudではクロスオリジン制限があるため、失敗した場合は100vhに頼る
                        const availableHeight = window.parent.innerHeight - 250;
                        if (availableHeight > 200) {{
                            document.querySelector('.unified-container').style.height = availableHeight + 'px';
                        }}
                    }} catch (e) {{
                        // フォールバック: 特殊なCSSを使わず、親側のCSSインジェクションに任せる
                        document.querySelector('.unified-container').style.height = 'calc(100vh - 20px)';
                    }}
                }};

                const cols = document.querySelectorAll('.trans-column-wrapper');
                let isSyncing = false;
                cols.forEach(col => {{
                    col.addEventListener('scroll', function() {{
                        if (isSyncing) return;
                        isSyncing = true;
                        const scrollTop = this.scrollTop;
                        cols.forEach(c => {{
                            if (c !== this) c.scrollTop = scrollTop;
                        }});
                        setTimeout(() => {{ isSyncing = false; }}, 50);
                    }});
                }});

                window.addEventListener('resize', () => {{
                    syncRowHeights();
                    adjustToViewport();
                }});
                
                setTimeout(() => {{
                    syncRowHeights();
                    adjustToViewport();
                }}, 100);
                setTimeout(syncRowHeights, 500);
                setTimeout(syncRowHeights, 3000);
            }})();
        </script>
    </body>
    </html>
    """
                # 親側にCSSを注入して、iframe自体の高さを動的に制御する（クロスオリジン対策）
                st.markdown(f"""
                <style>
                    iframe[title="st.components.v1.html"] {{
                        height: calc(100vh - 300px) !important;
                        min-height: 400px !important;
                    }}
                </style>
                """, unsafe_allow_html=True)
                
                components.html(html_content, height=1200, scrolling=False)
        else:
            st.info("元記事のURLを入力してください。")

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
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 操作ボタン群
                col1, col2, col3, col_space = st.columns([1.5, 1.5, 2.5, 5.5], gap="medium")
                
                with col1:
                    if st.button("全画像を選択", key="all_v9", use_container_width=True):
                        for i in range(len(image_urls)):
                            st.session_state[f"img_chk_v9_{i}"] = True
                            st.session_state[f"chk_v9_{i}"] = True # Widget keyも更新
                            st.session_state.sel_imgs.add(i)
                        st.rerun()
                
                with col2:
                    if st.button("全選択を解除", key="none_v9", use_container_width=True):
                        for i in range(len(image_urls)):
                            st.session_state[f"img_chk_v9_{i}"] = False
                            st.session_state[f"chk_v9_{i}"] = False # Widget keyも更新
                            st.session_state.sel_imgs.discard(i)
                        st.rerun()
                
                with col3:
                    # 選択状態をウィジェットの状態から直接再計算する（"1回遅れ"を防ぐため）
                    current_sel_indices = [
                        i for i in range(len(image_urls))
                        if st.session_state.get(f"chk_v9_{i}", False)
                    ]
                    target_urls = [image_urls[i] for i in current_sel_indices]
                    sel_count = len(current_sel_indices)
                    
                    # session_state.sel_imgs も一応同期しておく
                    st.session_state.sel_imgs = set(current_sel_indices)
                    
                    if sel_count == 1:
                        # 1枚のみ選択: 直接ダウンロード（zip化しない）
                        single_url = target_urls[0]
                        single_idx = current_sel_indices[0]
                        img_b64_single, _, img_fmt_single = fetch_image_data_v10(single_url, base_url)
                        if img_b64_single:
                            import base64
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
                                    use_container_width=True
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
                                use_container_width=True
                            )
                    else:
                        st.markdown("""
                        <div style="
                            padding: 10px;
                            border: 1px dashed #cbd5e1;
                            border-radius: 8px;
                            background-color: #f8fafc;
                            color: #64748b;
                            text-align: center;
                            font-size: 0.9em;
                        ">
                            画像を選択してください
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
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
                                h_c1, h_c2, h_c3 = st.columns([2.5, 2.5, 5])
                                
                                with h_c1:
                                    # Toggle Button (Select)
                                    btn_label = "■ 選択中" if is_selected else "□ 選択"
                                    btn_type = "primary" if is_selected else "secondary"
                                    
                                    if st.button(btn_label, key=f"btn_card_{abs_idx}", type=btn_type, use_container_width=True):
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
                                        # Already saved - show completed state
                                        st.markdown("""
                                        <div style="
                                            padding: 6px 12px;
                                            background: #dcfce7;
                                            border: 1px solid #86efac;
                                            border-radius: 8px;
                                            text-align: center;
                                            color: #16a34a;
                                            font-weight: 600;
                                            font-size: 0.85em;
                                        ">✓ 保存済</div>
                                        """, unsafe_allow_html=True)
                                    elif img_b64:
                                        # Not saved yet - show download button
                                        import base64
                                        try:
                                            b64_data = img_b64.split(",", 1)[1]
                                            img_bytes = base64.b64decode(b64_data)
                                            ext = img_fmt.lower() if img_fmt else "jpg"
                                            if ext == "jpeg":
                                                ext = "jpg"
                                            
                                            if st.download_button(
                                                label="保存",
                                                data=img_bytes,
                                                file_name=f"image_{abs_idx + 1}.{ext}",
                                                mime=f"image/{img_fmt.lower() if img_fmt else 'jpeg'}",
                                                key=f"dl_single_{abs_idx}",
                                                use_container_width=True
                                            ):
                                                st.session_state[saved_key] = True
                                                st.rerun()
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