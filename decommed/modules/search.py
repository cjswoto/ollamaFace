import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

def perform_web_search(query):
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(search_url, headers=headers, timeout=10)

    if response.status_code != 200:
        return f"Error: Search engine returned status code {response.status_code}"

    soup = BeautifulSoup(response.text, "html.parser")
    result_divs = soup.find_all("div", class_="tF2Cxc")

    results = []
    for div in result_divs[:3]:
        title_tag = div.find("h3")
        title = title_tag.get_text(strip=True) if title_tag else "No title"
        snippet_tag = div.find("span", class_="aCOpRe")
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No snippet"
        url_tag = div.find("a", href=True)
        url = url_tag["href"] if url_tag else "No URL"
        results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {url}\n")

    return "\n".join(results) if results else "No search results found."
