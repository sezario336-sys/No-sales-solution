from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def audit_etsy_shop(url_or_name):
    clean_input = url_or_name.strip().rstrip('/')
    if 'etsy.com' in clean_input:
        shop_url = clean_input if clean_input.startswith('http') else 'https://' + clean_input
        shop_name = shop_url.split('/shop/')[-1].split('/')[0]
    else:
        shop_name = clean_input
        shop_url = f"https://www.etsy.com/shop/{shop_name}"

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(shop_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, "Store not found or inaccessible. Please verify the URL or Shop Name."
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        issues = []
        passes = []
        score = 100

        # 1. Check Shop Announcement / Bio
        announcement = soup.find('div', {'class': re.compile('.*announcement.*|.*shop-message.*')})
        if not announcement or len(announcement.text.strip()) < 20:
            issues.append("Missing or short Shop Announcement. Reduces Etsy SEO ranking.")
            score -= 15
        else:
            passes.append("Active Shop Announcement detected.")

        # 2. Check About Section
        about_section = soup.find('div', {'id': 'about'}) or soup.find('section', {'class': re.compile('.*about.*')})
        if not about_section:
            issues.append("No 'About Section' detected. Buyers trust shops with brand stories 40% more.")
            score -= 20
        else:
            passes.append("Brand 'About Section' is properly configured.")

        # 3. Check Listing Titles & Keywords
        titles = [item.text.strip() for item in soup.find_all(['h3', 'h2'], {'class': re.compile('.*card-title.*|.*listing-title.*')})]
        if titles:
            short_titles = [t for t in titles if len(t) < 40]
            if short_titles:
                issues.append(f"Found {len(short_titles)} listings with short titles (<40 chars). Missing long-tail keywords.")
                score -= 15
            else:
                passes.append("Listing titles utilize strong long-tail keyword lengths.")
        else:
            issues.append("Unable to index listings. Store may be empty or under vacation mode.")
            score -= 25

        # 4. Check Shop Banner
        banner = soup.find('img', {'class': re.compile('.*banner.*|.*cover-photo.*')})
        if not banner:
            issues.append("Missing custom Shop Cover Banner. Weak visual branding.")
            score -= 15
        else:
            passes.append("Custom Shop Cover Banner is active.")

        # Final score adjustments
        score = max(score, 35)
        score_color = "#10b981" if score > 75 else ("#f59e0b" if score > 50 else "#ef4444")
        status_text = "Optimized" if score > 75 else ("Needs Work" if score > 50 else "Critical Issues Found")

        return {
            'shop_name': shop_name.capitalize(),
            'score': score,
            'score_color': score_color,
            'status_text': status_text,
            'issues': issues,
            'passes': passes
        }, None

    except Exception as e:
        return None, "Failed to analyze shop. Please try again in a few moments."

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        shop_url = request.form.get('shop_url')
        if not shop_url:
            return render_template('index.html', error="Please enter a valid shop URL or name.")
        
        audit_result, error = audit_etsy_shop(shop_url)
        if error:
            return render_template('index.html', error=error)
            
        return render_template('index.html', audit=audit_result, shop_name=shop_url)
        
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
