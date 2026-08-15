import requests
from bs4 import BeautifulSoup
import os

# --- 1. YOUR CONFIGURATION ---
WEBHOOK_URL = 'https://discordapp.com/api/webhooks/1537156547451559976/diRdAktZqbduXoDS9KcIAuD3k1LOi5C-wjC27SHntnpiLqfVJF6j3PY5d0Ck3EF8jLMy' 
TARGET_URL = 'https://game8.co/games/Wuthering-Waves/archives/453149' # Example target
KNOWN_CODES_FILE = 'known_codes.txt'

def get_known_codes():
    if not os.path.exists(KNOWN_CODES_FILE):
        return set()
    with open(KNOWN_CODES_FILE, 'r') as f:
        return set(f.read().splitlines())

def save_new_code(code):
    with open(KNOWN_CODES_FILE, 'a') as f:
        f.write(f"{code}\n")

def send_discord_alert(code):
    payload = {
        "username": "LootBar Tracker",
        "content": f"🚨 **New Redeem Code Found!** 🚨\n\n**Code:** `{code}`\n\n*Redeem it in-game before it expires!*"
    }
    requests.post(WEBHOOK_URL, json=payload)

def scrape_codes():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(TARGET_URL, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    known_codes = get_known_codes()
    
    # --- 2. THE HTML TARGETS ---
    # This looks for standard bold text often used for codes. 
    # You will need to tweak this based on the specific website you scrape!
    code_elements = soup.find_all('b') 
    
    for item in code_elements:
        code = item.text.strip()
        
        # Basic filter to ensure it looks like a game code (all caps, numbers, > 5 chars)
        if len(code) > 5 and code.isupper() and code.isalnum():
            if code not in known_codes:
                print(f"Found new code: {code}")
                send_discord_alert(code)
                save_new_code(code)

if __name__ == '__main__':
    print("Scanning for new codes...")
    scrape_codes()
    print("Scan complete.")

if __name__ == '__main__':
    print("Scanning for new codes...")
    scrape_codes()
    print("Scan complete.")