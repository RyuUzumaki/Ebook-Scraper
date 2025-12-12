import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def get_epub_link(book_details_url):
    """
    Scrapes the Standard Ebooks details page to find the direct download link
    for the 'Compatible epub' edition.
    """

    # We still need headers to prevent Standard Ebooks from blocking the *scraper*
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(book_details_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # --- STRATEGY 1: Best Match (Look for label "Compatible epub") ---
        # This guarantees we get the standard edition, not the advanced/kepub ones.
        for link in soup.find_all("a", href=True):
            if "Compatible epub" in link.text:
                return urljoin("https://standardebooks.org", str(link["href"]))

        # --- STRATEGY 2: Safe Fallback ---
        # If the label changes, look for the URL pattern.
        for link in soup.find_all("a", href=True):
            href_str = str(link["href"])

            # Logic: Must be in downloads folder, be an epub, and NOT be special editions
            if (
                "/downloads/" in href_str
                and href_str.endswith(".epub")
                and "kepub" not in href_str
                and "advanced" not in href_str
            ):
                return urljoin("https://standardebooks.org", href_str)

        return None

    except Exception as e:
        print(f"Error extracting download link: {e}")
        return None
