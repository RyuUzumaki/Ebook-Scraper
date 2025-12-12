import requests
from bs4 import BeautifulSoup
from extensions import cache


@cache.memoize(timeout=3600)
def get_single_book_details(book_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(book_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # 1. Get Title
        title_tag = soup.find(attrs={"property": "schema:name"})
        title = title_tag.text if title_tag else "Unknown Title"

        # 2. Get Author
        author_tag = soup.find(attrs={"property": "schema:author"})
        author = author_tag.text if author_tag else "Unknown Author"

        # 3. Get Description & CLEAN IT
        desc_section = soup.find("section", id="description")
        description = "No description available."

        if desc_section:
            # Find the unwanted donation aside
            donation_box = desc_section.find("aside", class_="donation")
            if donation_box:
                donation_box.decompose()

            description = desc_section.decode_contents()

        # 4. Get Cover Image
        img_tag = soup.find("meta", property="og:image")
        image_url = img_tag["content"] if img_tag else None

        return {
            "title": title,
            "author": author,
            "description": description,
            "image_url": image_url,
            "original_url": book_url,
        }

    except Exception as e:
        print(f"Error getting details: {e}")
        return None
