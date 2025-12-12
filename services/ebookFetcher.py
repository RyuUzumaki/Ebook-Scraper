import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from extensions import cache


@cache.memoize(timeout=3600)
def get_ebooks(page_number=1, search_query=None, category=None):

    # Defaults
    base_url = "https://standardebooks.org/ebooks"
    params = {}

    # --- LOGIC START ---

    # CASE A: SEARCH IS ACTIVE (Uses Query Params)
    # URL: /ebooks?query=foo&page=2
    if search_query:
        base_url = "https://standardebooks.org/ebooks"
        params["query"] = search_query
        params["page"] = page_number

        if category:
            params["tags[]"] = category

    # CASE B: BROWSING (Uses URL Path)
    # URL: /ebooks/page/2
    else:
        # Determine Base
        if category:
            base_url = f"https://standardebooks.org/subjects/{category}"
        else:
            base_url = "https://standardebooks.org/ebooks"

        # Append Page to Path (only if not page 1)
        # IMPORTANT: Do NOT add a trailing slash here, it causes 404s
        if page_number > 1:
            base_url = f"{base_url}?page={page_number}"

        params = {}

    # --- LOGIC END ---

    # Stronger Headers to look like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://standardebooks.org/",
    }

    try:
        print(f"DEBUG: Requesting {base_url} | Params: {params}")

        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # DEBUG: Print the page title to see if we are on the right page
        title_tag = soup.find("title")
        page_title = title_tag.text.strip() if title_tag else "No Title"
        print(f"DEBUG PAGE TITLE: {page_title}")

        # Check for Next Button
        next_button = soup.find("a", attrs={"rel": "next"})
        has_next_page = True if next_button else False

        ebooks = []

        # Try finding the list with a flexible selector
        list_container = soup.select_one("ol.ebooks-list")

        if not list_container:
            print(
                f"DEBUG ERROR: Could not find <ol class='ebooks-list'> on page: {page_title}"
            )
            return [], False

        for item in list_container.find_all("li"):
            title_tag = item.find(attrs={"property": "schema:name"})
            link_tag = item.find("a")
            author_tag = item.find(attrs={"property": "schema:author"})

            if link_tag and title_tag:
                full_link = urljoin("https://standardebooks.org", str(link_tag["href"]))
                author_text = (
                    author_tag.text.strip() if author_tag else "Unknown Author"
                )

                data = {
                    "title": title_tag.text,
                    "link": full_link,
                    "summary": author_text,
                }
                ebooks.append(data)

        print(f"DEBUG: Found {len(ebooks)} books.")
        return ebooks, has_next_page

    except Exception as e:
        print(f"DEBUG CRITICAL ERROR: {e}")
        return [], False
