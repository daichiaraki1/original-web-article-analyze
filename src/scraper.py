import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin
import streamlit as st

@dataclass
class ArticleContent:
    url: str
    title: str
    text: str
    image_urls: List[str]
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    structured_html_parts: Optional[List[dict]] = None

def fetch_html(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.error(f"URL取得エラー: {e}")
        return ""

def parse_wechat_article(html: str, url: str) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    title_el = soup.find("h1", id="activity-name") or soup.find("meta", property="og:title")
    if title_el:
        title = title_el.get("content", "") if title_el.name == "meta" else title_el.get_text(strip=True)

    publisher = ""
    pub_el = soup.find("strong", class_="profile_nickname") or soup.find("a", id="js_name")
    if pub_el: publisher = pub_el.get_text(strip=True)

    publish_date = ""
    date_el = soup.find("em", id="publish_time") or soup.find("span", class_="post-date")
    if date_el: publish_date = date_el.get_text(strip=True)

    content_el = soup.find("div", id="js_content") or soup.find("article") or soup.body
    if not content_el: return ArticleContent(url, title, "", [])

    image_urls = []
    structured_html_parts = []
    plain_text_parts = []

    for tag in content_el.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img'], recursive=True):
        if tag.name == 'img':
            src = tag.get("data-src") or tag.get("src")
            if src:
                abs_url = urljoin(url, src)
                if abs_url.startswith("http") and abs_url not in image_urls:
                    image_urls.append(abs_url)
        elif tag.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            txt = tag.get_text(strip=True)
            if txt and len(txt) > 1:
                structured_html_parts.append({"tag": tag.name, "text": txt})
                plain_text_parts.append(txt)


    # Prepend title to structured_html_parts so it appears in translation view
    if title:
        structured_html_parts.insert(0, {"tag": "h3", "text": title})

    return ArticleContent(url, title, "\n\n".join(plain_text_parts), image_urls, publisher, publish_date, structured_html_parts)

@st.cache_data(show_spinner=False)
def load_article_v9(url: str) -> Optional[ArticleContent]:
    if not url or not url.startswith("http"): return None
    html = fetch_html(url)
    return parse_wechat_article(html, url) if html else None
