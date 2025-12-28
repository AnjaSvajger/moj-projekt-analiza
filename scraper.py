import os
import json
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def count_stars(element):
    """Prešteje SVG zvezdice"""
    try:
        stars = element.find_elements(By.XPATH, ".//*[local-name()='path' and @fill='#ffce31']")
        return len(stars) if len(stars) > 0 else 5
    except:
        return 5

def main():
    print("="*60)
    print("🚀 WEB SCRAPER")
    print("="*60)
    
    # Nastavitve
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir, 'scraped_data')
    os.makedirs(data_folder, exist_ok=True)
    
    # Zagon Chrome
    print("\n⚙️  Zaganjam Chrome...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    all_data = {
        "products": [],
        "reviews": [],
        "testimonials": []
    }
    
    try:
        # ==========================================
        # 1. PRODUCTS
        # ==========================================
        print("\n📦 PRODUCTS - Scraping...")
        seen_products = set()
        page = 1
        
        while page <= 10:
            driver.get(f"https://web-scraping.dev/products?page={page}")
            time.sleep(2)
            
            products = driver.find_elements(By.CSS_SELECTOR, "div[class*='product']")
            
            if not products:
                print(f"   Stran {page}: Ni produktov")
                break
            
            added = 0
            for p in products:
                try:
                    text = p.text.strip()
                    if not text or len(text) < 5:
                        continue
                    
                    lines = text.split('\n')
                    name = lines[0].strip()
                    
                    if len(name) < 3 or name.lower() in ['log in', 'sign up', 'products']:
                        continue
                    
                    # Najdi ceno
                    price = "$0.00"
                    for line in lines:
                        if '$' in line:
                            match = re.search(r'\$\d+\.\d{2}', line)
                            if match:
                                price = match.group(0)
                                break
                    
                    product_id = f"{name}_{price}"
                    if product_id not in seen_products:
                        seen_products.add(product_id)
                        all_data["products"].append({
                            "name": name,
                            "price": price
                        })
                        added += 1
                except:
                    continue
            
            print(f"   Stran {page}: +{added} | Skupaj: {len(all_data['products'])}")
            
            if added == 0:
                break
            
            page += 1
        
        print(f"   ✅ Skupaj: {len(all_data['products'])} products\n")
        
        # ==========================================
        # 2. REVIEWS
        # ==========================================
        print("⭐ REVIEWS - Scraping...")
        driver.get("https://web-scraping.dev/reviews")
        time.sleep(3)
        
        seen_reviews = set()
        stop_scraping = False
        clicks = 0
        
        while not stop_scraping and clicks < 15:
            reviews = driver.find_elements(By.CLASS_NAME, "review")
            
            added = 0
            for r in reviews:
                try:
                    text = r.text.strip()
                    if not text:
                        continue
                    
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    
                    # Najdi datum
                    date_str = ""
                    year = 0
                    for line in lines:
                        if re.search(r'20\d{2}', line):
                            date_str = line
                            year_match = re.search(r'(20\d{2})', line)
                            if year_match:
                                year = int(year_match.group(1))
                            break
                    
                    # Ustavi pri starih
                    if year > 0 and year < 2023:
                        print(f"   ⛔ Najden review iz {year} - ustavljam")
                        stop_scraping = True
                        break
                    
                    if not date_str:
                        continue
                    
                    # Review text (najdaljša vrstica)
                    review_text = max(lines, key=len, default='')
                    
                    if len(review_text) < 10:
                        continue
                    
                    rating = count_stars(r)
                    
                    review_id = f"{review_text[:30]}_{date_str}"
                    if review_id not in seen_reviews:
                        seen_reviews.add(review_id)
                        all_data["reviews"].append({
                            "date": date_str,
                            "review_text": review_text,
                            "rating": rating
                        })
                        added += 1
                except:
                    continue
            
            if added > 0:
                print(f"   +{added} reviews | Skupaj: {len(all_data['reviews'])}")
            
            if stop_scraping:
                break
            
            # Klikni Load More
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                load_btn = driver.find_element(By.ID, "page-load-more")
                if load_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", load_btn)
                    clicks += 1
                    time.sleep(2)
                else:
                    break
            except:
                print("   Load More gumb ni najden")
                break
        
        print(f"   ✅ Skupaj: {len(all_data['reviews'])} reviews\n")
        
        # ==========================================
        # 3. TESTIMONIALS
        # ==========================================
        print("💬 TESTIMONIALS - Scraping...")
        driver.get("https://web-scraping.dev/testimonials")
        time.sleep(3)
        
        seen_testimonials = set()
        last_height = 0
        scrolls = 0
        
        while scrolls < 10:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            testimonials = driver.find_elements(By.XPATH, "//div[contains(@class, 'testimonial')]")
            
            added = 0
            for t in testimonials:
                try:
                    text = t.text.strip()
                    
                    if not text or len(text) < 10 or len(text) > 400:
                        continue
                    
                    if any(word in text.lower() for word in ['take a look', 'collection', 'navigation']):
                        continue
                    
                    clean_text = ' '.join(text.split())
                    
                    if clean_text not in seen_testimonials:
                        seen_testimonials.add(clean_text)
                        rating = count_stars(t)
                        all_data["testimonials"].append({
                            "text": clean_text,
                            "rating": rating
                        })
                        added += 1
                except:
                    continue
            
            if added > 0:
                print(f"   Scroll {scrolls+1}: +{added} | Skupaj: {len(all_data['testimonials'])}")
            
            if new_height == last_height:
                print("   Ni več vsebine")
                break
            
            last_height = new_height
            scrolls += 1
        
        print(f"   ✅ Skupaj: {len(all_data['testimonials'])} testimonials\n")
        
    except Exception as e:
        print(f"\n❌ NAPAKA: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("\n🔒 Brskalnik zaprt")
    
    # ==========================================
    # SHRANJEVANJE
    # ==========================================
    print("\n" + "="*60)
    print("💾 SHRANJEVANJE...")
    print("="*60)
    
    # Products
    if all_data["products"]:
        df = pd.DataFrame(all_data["products"])
        df.to_json(os.path.join(data_folder, 'products.json'), orient='records', indent=4)
        df.to_csv(os.path.join(data_folder, 'products.csv'), index=False)
        print(f"✓ Products: {len(all_data['products'])}")
    
    # Reviews
    if all_data["reviews"]:
        df = pd.DataFrame(all_data["reviews"])
        df.to_json(os.path.join(data_folder, 'reviews.json'), orient='records', indent=4)
        df.to_csv(os.path.join(data_folder, 'reviews.csv'), index=False)
        print(f"✓ Reviews: {len(all_data['reviews'])}")
    
    # Testimonials
    if all_data["testimonials"]:
        df = pd.DataFrame(all_data["testimonials"])
        df.to_json(os.path.join(data_folder, 'testimonials.json'), orient='records', indent=4)
        df.to_csv(os.path.join(data_folder, 'testimonials.csv'), index=False)
        print(f"✓ Testimonials: {len(all_data['testimonials'])}")
    
    print("\n" + "="*60)
    print("📊 POVZETEK")
    print("="*60)
    print(f"Products:     {len(all_data['products'])}")
    print(f"Reviews:      {len(all_data['reviews'])}")
    print(f"Testimonials: {len(all_data['testimonials'])}")
    print(f"\n📁 {data_folder}/")
    print("\n✅ KONČANO!\n")

if __name__ == "__main__":
    main()