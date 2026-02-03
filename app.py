import textwrap
import streamlit as st
from src.scraper import load_article_v9
from src.translator import translate_paragraphs
from src.utils import create_images_zip, fetch_image_as_base64, make_diff_html

# --- メイン UI ---
def main():
    st.set_page_config(layout="wide", page_title="中国メディア解析ツール")

    st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; color: #1e293b !important; }
        h1, h2, h3, h4, h5, p, span, label, div { color: #1e293b !important; }
        
        /* URL入力欄のUI改善 */
        .stTextInput input {
            background-color: white !important; color: #1e293b !important;
            caret-color: #3b82f6 !important; border: 1px solid #cbd5e1 !important;
            outline: none !important;
        }
        .stTextInput input:focus { background-color: #f8fafc !important; border-color: #3b82f6 !important; }

        /* ボタン */
        .stButton > button {
            background-color: #ffffff !important; color: #000000 !important;
            border: 1px solid #94a3b8 !important; font-weight: 700 !important;
        }

        /* 統合コンテナ */
        .unified-container {
            display: flex; flex-direction: column; height: 82vh; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: white;
        }
        .unified-header { display: flex; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
        .header-cell { flex: 1; padding: 12px 20px; border-right: 1px solid #e2e8f0; font-weight: bold; color: #1e293b; }
        
        .content-columns { display: flex; flex: 1; overflow: hidden; }
        .scroll-pane { flex: 1; overflow-y: auto; background: white; border-right: 1px solid #e2e8f0; }
        
        /* 段落ブロック */
        .paragraph-block { padding: 15px 20px; border-bottom: 1px solid #f8fafc; position: relative; line-height: 1.8; color: #1e293b; }
        
        /* 翻訳エンジンラベル（コピー対象外に設定） */
        .engine-label { 
            font-size: 9px; color: #94a3b8; position: absolute; top: 3px; right: 8px; 
            background: #f1f5f9; padding: 2px 5px; border-radius: 4px;
            user-select: none; /* コピーを防止 */
            pointer-events: none; /* クリック操作などを無効化 */
        }

        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 6px; padding: 8px 16px; color: #475569 !important; font-weight: 600 !important; }
        .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
        
        /* チェックボックスの視認性改善 */
        input[type="checkbox"] { accent-color: #3b82f6 !important; background-color: white !important; }
    </style>
    
    <script>
        function setupSync() {
            const left = document.getElementById('left-pane');
            const right = document.getElementById('right-pane');
            if (!left || !right) return;

            // 1. 高さを揃える
            const lBlocks = left.getElementsByClassName('paragraph-block');
            const rBlocks = right.getElementsByClassName('paragraph-block');
            const len = Math.min(lBlocks.length, rBlocks.length);
            for (let i = 0; i < len; i++) {
                lBlocks[i].style.height = 'auto';
                rBlocks[i].style.height = 'auto';
                const h = Math.max(lBlocks[i].offsetHeight, rBlocks[i].offsetHeight);
                lBlocks[i].style.height = h + 'px';
                rBlocks[i].style.height = h + 'px';
            }

            // 2. スクロール同期（精密な連動ロジック）
            if (!window.isSyncActive) {
                window.isSyncActive = true;
                const sync = (src, dest) => {
                    src.onscroll = () => {
                        if (src.isScrolling) return;
                        dest.isScrolling = true;
                        dest.scrollTop = src.scrollTop;
                        setTimeout(() => { dest.isScrolling = false; }, 50);
                    };
                };
                sync(left, right);
                sync(right, left);
            }
        }
        setInterval(setupSync, 1000);
        new MutationObserver(setupSync).observe(document.body, { childList: true, subtree: true });
    </script>
    """, unsafe_allow_html=True)

    st.title("🇨🇳 中国メディア記事 解析＆比較ツール")

    c1, c2 = st.columns(2)
    src_url = c1.text_input("元記事URL", value=st.session_state.get("s_url_v9", ""), key="src_in_v9")
    cmp_url = c2.text_input("比較用URL (任意)", value=st.session_state.get("c_url_v9", ""), key="cmp_in_v9")
    st.session_state.s_url_v9 = src_url
    st.session_state.c_url_v9 = cmp_url

    src_article = load_article_v9(src_url) if src_url else None
    cmp_article = load_article_v9(cmp_url) if cmp_url else None

    tab_titles = ["📄 記事内容", "🖼 画像一覧 / ZIP"]
    if src_article and cmp_article: tab_titles.append("🔍 文章比較")
    tabs = st.tabs(tab_titles)

    # --- タブ1: 記事内容 ---
    with tabs[0]:
        if src_article:
            if not cmp_article:
                t_key = f"t_v9_{src_url}"
                if t_key not in st.session_state:
                    st.session_state[t_key] = translate_paragraphs(src_article.structured_html_parts)
                    st.session_state[f"t_ttl_v9_{src_url}"] = translate_paragraphs([{"tag":"h1", "text":src_article.title}])[0]["text"]
                r_data = st.session_state[t_key]
                r_title = st.session_state[f"t_ttl_v9_{src_url}"]
                r_header = "日本語翻訳"
                is_trans = True
            else:
                r_data = cmp_article.structured_html_parts
                r_title = cmp_article.title
                r_header = "比較対象記事"
                is_trans = False

            l_blocks = [f"<div class='paragraph-block'><span style='font-size:0.8em; color:#64748b;'>{src_article.publisher}</span><h3>{src_article.title}</h3></div>"]
            for p in src_article.structured_html_parts:
                l_blocks.append(f"<div class='paragraph-block'><{p['tag']}>{p['text']}</{p['tag']}></div>")

            r_blocks = [f"<div class='paragraph-block'><h3>{r_title}</h3></div>"]
            for i in range(len(r_data)):
                p = r_data[i]
                # エンジンラベルは別コンテナにはしない（レイアウトが崩れるため）
                # 代わりに CSS で user-select: none をかけてコピーを防ぐ
                eng = f"<span class='engine-label'>{p.get('engine','')}</span>" if is_trans else ""
                r_blocks.append(f"<div class='paragraph-block'>{eng}<{p['tag']}>{p['text']}</{p['tag']}></div>")

            final_layout = textwrap.dedent(f"""
                <div class="unified-container">
                    <div class="unified-header"><div class="header-cell">元記事 (原文)</div><div class="header-cell">{r_header}</div></div>
                    <div class="content-columns">
                        <div id="left-pane" class="scroll-pane">{"".join(l_blocks)}</div>
                        <div id="right-pane" class="scroll-pane">{"".join(r_blocks)}</div>
                    </div>
                </div>
            """).strip()
            st.markdown(final_layout, unsafe_allow_html=True)
        else:
            st.info("元記事のURLを入力してください。")

    # --- タブ2: 画像一覧 ---
    with tabs[1]:
        if src_article and src_article.image_urls:
            if "sel_imgs" not in st.session_state: st.session_state.sel_imgs = set()
            b1, b2, b3 = st.columns([1, 1, 3])
            if b1.button("すべて選択", key="all_v9"):
                for i in range(len(src_article.image_urls)):
                    st.session_state[f"img_chk_v9_{i}"] = True
                    st.session_state.sel_imgs.add(i)
                st.rerun()
            if b2.button("選択解除", key="none_v9"):
                for i in range(len(src_article.image_urls)):
                    st.session_state[f"img_chk_v9_{i}"] = False
                    st.session_state.sel_imgs.discard(i)
                st.rerun()
            
            if st.session_state.sel_imgs:
                urls = [src_article.image_urls[i] for i in st.session_state.sel_imgs]
                zip_data = create_images_zip(urls, src_url)
                b3.download_button(f"ダウンロード ({len(st.session_state.sel_imgs)}枚)", zip_data, "images.zip", key="dl_v9")

            img_cols = st.columns(4)
            for i, img_url in enumerate(src_article.image_urls):
                with img_cols[i % 4]:
                    is_checked = st.checkbox(f"選択 #{i+1}", key=f"img_chk_v9_{i}")
                    if is_checked: st.session_state.sel_imgs.add(i)
                    else: st.session_state.sel_imgs.discard(i)
                    img_base64 = fetch_image_as_base64(img_url, src_url)
                    st.markdown(f'<div style="border:2px solid {"#3b82f6" if is_checked else "#f1f5f9"}; border-radius:10px; padding:10px; margin-bottom:10px; background:white;">', unsafe_allow_html=True)
                    if img_base64: st.image(img_base64, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- タブ3: 文章比較 ---
    if len(tab_titles) > 2:
        with tabs[2]:
            l_diff, r_diff = make_diff_html(src_article.text, cmp_article.text)
            st.markdown(textwrap.dedent(f"""
                <div class="unified-container" style="height:75vh;">
                    <div class="unified-header"><div class="header-cell">元記事 差分</div><div class="header-cell">比較記事 差分</div></div>
                    <div class="content-columns">
                        <div id="diff-l" class="scroll-pane" style="padding:10px;">{l_diff}</div>
                        <div id="diff-r" class="scroll-pane" style="padding:10px;">{r_diff}</div>
                    </div>
                </div>
            """).strip(), unsafe_allow_html=True)

if __name__ == "__main__":
    main()