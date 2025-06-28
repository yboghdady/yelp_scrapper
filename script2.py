import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
# ...existing code...
proxy = None  # Set your proxy here if needed, e.g., {"server": "http://your_proxy:port"}
async def run_playwright_bs4_scraper():
    url = "https://www.yelp.com/search?find_desc=Restaurants&find_loc=Las+Vegas"
    scraped_data = []

    async with async_playwright() as p:
        browser_args = {
            "headless": False,
            "args": [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
            ],
        }

        if proxy:
            browser_args["proxy"] = proxy

        browser = await p.chromium.launch(**browser_args)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
            locale="en-US"
        )

        page = await context.new_page()

        for page_num in range(2):  # Scrape first 2 pages
            page_url = url + (f"&start={page_num*10}" if page_num > 0 else "")
            print(f"Navigating to page {page_num+1}...")
            await page.goto(page_url, wait_until="domcontentloaded", timeout=60000)

            print("Waiting CAPTCHA..")
            await page.wait_for_timeout(20000)  # Wait 20 seconds for manual CAPTCHA solving

            # Scroll to the bottom to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(5000)

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")
            cards = soup.select("div.container__09f24__FeTO6")

            print(f"Found {len(cards)} restaurant cards on page {page_num + 1}.")

            detail_links = []
            for card in cards[:20]:  # Limit to first 20 cards for demo
                a_tag = card.select_one("h3 a")
                if a_tag and a_tag.has_attr("href"):
                    link = "https://www.yelp.com" + a_tag['href'].split("?")[0]  # clean params
                    detail_links.append(link)

            for i, detail_url in enumerate(detail_links, 1):
                try:
                    print(f"\n\U0001F4CD Visiting: {detail_url}")
                    await page.goto(detail_url, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)

                    detail_html = await page.content()
                    detail_soup = BeautifulSoup(detail_html, "lxml")

                    name_tag = detail_soup.find("h1")
                    phone_tag = detail_soup.find("p", string=re.compile(r"\(\d{3}\)"))
                    price_tag = detail_soup.find("span", string=re.compile(r"^\$+"))
                    category_tag = detail_soup.select('span[data-testid= "BizHeaderCategory" ] a')
                    address_tag = detail_soup.select_one("address")
                    website_tag = detail_soup.find("a", href=re.compile(r"^https?://"))
                    open_hours_tag = detail_soup.find("table")
                    amenities_tags = detail_soup.find_all("span", string=re.compile(r"(Outdoor|Reservation|Takeout|Delivery)", re.IGNORECASE))
                
                    highlights_tags = detail_soup.find_all("span", string=re.compile(r"(popular|highlight)", re.IGNORECASE))
                    
                    health_score_tag = detail_soup.find("div", string=re.compile("health", re.IGNORECASE))


                    data = {
                        "Name": name_tag.text.strip() if name_tag else "N/A",
                        "Category": ", ".join(tag.text.strip() for tag in category_tag) if category_tag else "N/A",
                        "Price": price_tag.text.strip() if price_tag else "N/A",
                        "Address": address_tag.text.strip() if address_tag else "N/A",
                        "Website": website_tag['href'] if website_tag else "N/A",
                        "Phone Number": phone_tag.text.strip() if phone_tag else "N/A",
                        "Open Hours": open_hours_tag.text.strip() if open_hours_tag else "N/A",
                        "Health Score": health_score_tag.text.strip() if health_score_tag else "N/A",
                        "Amenities": ", ".join(tag.text.strip() for tag in amenities_tags) if amenities_tags else "N/A",
                        "Highlights": ", ".join(tag.text.strip() for tag in highlights_tags) if highlights_tags else "N/A",
                    }
                    if (
                        data["Name"] == "N/A"
                        or "We’re sorry" in data["Name"]
                        or "can't find the page" in data["Name"]
                    ):
                        # print(f"⏭️ Skipping invalid restaurant: {data['Name']}")
                        continue

                    # print(f"\n📍 Restaurant {i}")
                    # for k, v in data.items():
                    #     print(f"  {k}: {v}")

                    scraped_data.append(data)

                except Exception as e:
                    print(f"Error parsing restaurant {i}: {e}")

        # Save to CSV
        if scraped_data:
            df = pd.DataFrame(scraped_data)
            df.to_csv("yelp_restaurants_bs4.csv", index=False)
            print(" Data saved to yelp_restaurants.csv")
        else:
            print(" No valid data scraped.")

        await browser.close()
# ...existing code...
if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(run_playwright_bs4_scraper())
    end_time = time.time()
    print(f"Scraping completed in {end_time - start_time:.2f} seconds.")