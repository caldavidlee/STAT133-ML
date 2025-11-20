import os
import time
import requests
from playwright.sync_api import sync_playwright

def scrape_duckduckgo_images():
    # Configuration
    url = "https://duckduckgo.com/?q=profile+pictures&atb=v418-1&ia=images&iax=images"
    target_folder = "profilePhotos"
    target_count = 500
    max_scrolls = 1000  # Safety limit
    
    # Ensure directory exists
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        print(f"Created directory: {target_folder}")
    else:
        print(f"Directory exists: {target_folder}")

    print("Starting browser...")
    image_urls = set()
    
    with sync_playwright() as p:
        # Launch browser with custom context to mimic real user
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1024}
        )
        page = context.new_page()
        
        print(f"Navigating to {url}")
        page.goto(url)
        
        # Wait for initial load
        try:
            page.wait_for_selector("figure img", timeout=10000)
        except Exception:
            print("Warning: Initial selector wait timed out. Continuing anyway...")
        
        print(f"Scrolling to harvest images...")
        
        prev_count = 0
        stable_count = 0
        
        for i in range(max_scrolls):
            if len(image_urls) >= target_count:
                print(f"Reached target of {target_count} images.")
                break
                
            # Harvest URLs visible in current state
            # We execute JS to find all images that look like search results
            found_in_step = page.evaluate("""() => {
                const out = [];
                // Select images inside figures (DDG structure)
                const imgs = document.querySelectorAll('figure img');
                for (const img of imgs) {
                    let src = img.getAttribute('src') || img.getAttribute('data-src') || img.currentSrc;
                    if (src) {
                        // Fix protocol relative URLs
                        if (src.startsWith('//')) {
                            src = 'https:' + src;
                        }
                        // Filter for valid http links
                        if (src.startsWith('http')) {
                            out.push(src);
                        }
                    }
                }
                return out;
            }""")
            
            # Add new URLs to our set
            for src in found_in_step:
                image_urls.add(src)
            
            current_count = len(image_urls)
            print(f"Scroll {i+1}: Found {current_count} unique images so far...")
            
            # Check stability (if we aren't finding new ones)
            if current_count == prev_count:
                stable_count += 1
                if stable_count >= 5: # Stop if no new images for 5 scrolls
                    print("No new images found for several scrolls. Stopping.")
                    break
            else:
                stable_count = 0
                prev_count = current_count
                
            # Scroll down a chunk
            page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            time.sleep(0.5) # Short pause for loading
            
        browser.close()

    print(f"Total unique images found: {len(image_urls)}")
    print(f"Downloading images...")
    
    # Download images
    downloaded_count = 0
    for i, url in enumerate(list(image_urls)[:target_count]):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Determine extension or default to .jpg
                ext = ".jpg"
                if "png" in response.headers.get("Content-Type", ""):
                    ext = ".png"
                elif "webp" in response.headers.get("Content-Type", ""):
                    ext = ".webp"
                
                filename = f"image_{i+1:03d}{ext}"
                file_path = os.path.join(target_folder, filename)
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                downloaded_count += 1
                
                if downloaded_count % 50 == 0:
                    print(f"Downloaded {downloaded_count} images...")
            else:
                # print(f"Failed to download {url}: Status {response.status_code}")
                pass
        except Exception as e:
            print(f"Error downloading image {i}: {e}")

    print(f"Done! Successfully downloaded {downloaded_count} images to '{target_folder}'.")

if __name__ == "__main__":
    scrape_duckduckgo_images()
