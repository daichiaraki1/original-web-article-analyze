"""
Shenzhen Fan 記事生成モジュール
Gemini APIを使って中国語ニュース原文から日本語記事を自動生成する
"""
import google.generativeai as genai
import streamlit as st


# Shenzhen Fan 記事生成プロンプト
ARTICLE_GENERATION_PROMPT = """あなたは深センの日本人向け情報サイト「Shenzhen Fan」の編集者です。
以下の中国語テキストを元に、日本人が読むための客観的で有益な日本語記事を作成してください。

# 制約事項
1. **脱・誇張表現:** 原文にある「世界をリードする」「画期的な」といった中国語特有の誇張やプロパガンダ的な修飾語は削除し、事実（Fact）のみを抽出する。
2. **ターゲット:** 深セン在住、または深センのビジネス・テクノロジーに関心のある日本人。
3. **視点:** 「日本人にとってどういう意味があるか」「何が便利になるか」という視点で再構成する。
4. **構成:**
   - 【タイトル】（30文字以内、キャッチーに）
   - 【リード文】（3行で要約）
   - 【本文】（見出しを付け、冗長な部分はカットし、要点を箇条書き等で分かりやすく）
   - 【深センFan的視点】（現地日本人の生活やビジネスへの影響についての考察を一言追加）

# 出力トーン
- ビジネスライクだが、親しみやすい「Shenzhen Fan」らしいトーン。
- 語尾は「です・ます」調。

# 元記事情報
タイトル: {title}
メディア: {publisher}

# 元記事テキスト（中国語）
{chinese_text}
"""

# Gemini Safety Settings (shared with translator.py)
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]


def generate_article(
    chinese_text: str,
    gemini_api_key: str,
    model_name: str = "gemini-2.5-flash",
    article_title: str = "",
    publisher: str = "",
    output_placeholder=None,
) -> str:
    """
    中国語テキストからShenzhen Fan向け日本語記事を生成する。

    Args:
        chinese_text: 原文テキスト（中国語）
        gemini_api_key: Gemini APIキー
        model_name: 使用するGeminiモデル名
        article_title: 元記事のタイトル
        publisher: 元記事のメディア名
        output_placeholder: Streamlit placeholder（ストリーミング表示用）

    Returns:
        生成された日本語記事テキスト
    """
    if not chinese_text or not gemini_api_key:
        return ""

    # Configure Gemini
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(model_name)

    # Build prompt
    prompt = ARTICLE_GENERATION_PROMPT.format(
        title=article_title or "(タイトル不明)",
        publisher=publisher or "(メディア不明)",
        chinese_text=chinese_text,
    )

    # Generate with streaming
    full_text = ""

    try:
        response = model.generate_content(
            prompt,
            safety_settings=SAFETY_SETTINGS,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                full_text += chunk.text

                # Update placeholder with streaming content
                if output_placeholder:
                    output_placeholder.markdown(
                        f"""<div style="
                            color: #1e293b;
                            line-height: 2.0;
                            font-size: 15px;
                            padding: 20px 24px;
                            background: #ffffff;
                            border: 1px solid #e2e8f0;
                            border-radius: 12px;
                        ">{_format_article_html(full_text)}▌</div>""",
                        unsafe_allow_html=True,
                    )

        # Final render (remove cursor)
        if output_placeholder and full_text:
            output_placeholder.markdown(
                f"""<div style="
                    color: #1e293b;
                    line-height: 2.0;
                    font-size: 15px;
                    padding: 20px 24px;
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                ">{_format_article_html(full_text)}</div>""",
                unsafe_allow_html=True,
            )

        return full_text

    except Exception as e:
        error_msg = str(e)

        # Quota error handling
        if "429" in error_msg or "quota" in error_msg.lower():
            if output_placeholder:
                output_placeholder.error(
                    "⚠️ Gemini APIの利用制限に達しました。しばらく待ってから再試行してください。"
                )
            return f"[エラー] API利用制限: {error_msg}"

        if output_placeholder:
            output_placeholder.error(f"⚠️ 記事生成エラー: {error_msg}")
        return f"[エラー] {error_msg}"


def _format_article_html(text: str) -> str:
    """
    マークダウンテキストを簡易的なHTMLに変換する。
    Geminiの出力は通常マークダウン形式なので、見出しや箇条書きを整形する。
    """
    import re

    lines = text.split("\n")
    html_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_lines.append("<br>")
            continue

        # 見出し（### → h4, ## → h3, # → h2）
        if stripped.startswith("### "):
            html_lines.append(
                f"<h4 style='color:#334155; margin:16px 0 8px 0; font-size:1.05em;'>{stripped[4:]}</h4>"
            )
        elif stripped.startswith("## "):
            html_lines.append(
                f"<h3 style='color:#1e293b; margin:20px 0 10px 0; font-size:1.15em;'>{stripped[3:]}</h3>"
            )
        elif stripped.startswith("# "):
            html_lines.append(
                f"<h2 style='color:#0f172a; margin:20px 0 12px 0; font-size:1.3em;'>{stripped[2:]}</h2>"
            )
        # 箇条書き
        elif stripped.startswith("- ") or stripped.startswith("* "):
            html_lines.append(
                f"<div style='padding-left:16px; margin:4px 0;'>• {stripped[2:]}</div>"
            )
        # 太字のセクションヘッダー【…】
        elif stripped.startswith("【") and "】" in stripped:
            header_end = stripped.index("】") + 1
            header = stripped[:header_end]
            rest = stripped[header_end:]
            html_lines.append(
                f"<div style='font-weight:700; color:#1e40af; margin:18px 0 6px 0; font-size:1.1em;'>{header}</div>"
            )
            if rest.strip():
                html_lines.append(f"<div>{rest.strip()}</div>")
        else:
            # Bold markers: **text** → <strong>text</strong>
            formatted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", stripped)
            html_lines.append(f"<div style='margin:4px 0;'>{formatted}</div>")

    return "\n".join(html_lines)
