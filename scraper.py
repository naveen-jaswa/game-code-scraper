import json
import os
import re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
KNOWN_CODES_FILE = "known_codes.txt"
OUTPUT_JSON_FILE = "codes.json"

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
DISCORD_WEBHOOK_WUWA = os.environ.get("DISCORD_WEBHOOK_WUWA")

GAMES = {
    "genshin": {
        "name": "Genshin Impact",
        "url": "https://genshin-impact.fandom.com/wiki/Promotional_Codes",
        "webhook": DISCORD_WEBHOOK,
        "redeem_url": "https://genshin.hoyoverse.com/en/gift?code=",
    },
    "hsr": {
        "name": "Honkai: Star Rail",
        "url": "https://honkai-star-rail.fandom.com/wiki/Redemption_Code",
        "webhook": DISCORD_WEBHOOK,
        "redeem_url": "https://hsr.hoyoverse.com/gift?code=",
    },
    "wuwa": {
        "name": "Wuthering Waves",
        "url": "https://wutheringwaves.fandom.com/wiki/Redemption_Code",
        "webhook": DISCORD_WEBHOOK_WUWA or DISCORD_WEBHOOK,
        "redeem_url": None,  # In-game only
    },
    "zzz": {
        "name": "Zenless Zone Zero",
        "url": "https://zenless-zone-zero.fandom.com/wiki/Redemption_Code",
        "webhook": DISCORD_WEBHOOK,
        "redeem_url": "https://zenless.hoyoverse.com/redemption?code=",
    },
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_known_codes():
    if not os.path.exists(KNOWN_CODES_FILE):
        return set()
    with open(KNOWN_CODES_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_known_codes(known_codes):
    with open(KNOWN_CODES_FILE, "w", encoding="utf-8") as f:
        for code in sorted(known_codes):
            f.write(f"{code}\n")


def send_discord_alert(game_info, code, rewards):
    webhook_url = game_info["webhook"]
    if not webhook_url:
        return

    link_line = (
        f"\n🔗 **Redeem:** {game_info['redeem_url']}{code}"
        if game_info["redeem_url"]
        else "\n📱 *Redeem in-game (Settings → Redemption Code)*"
    )
    payload = {
        "username": "Redeem Hub Tracker",
        "content": (
            f"🚨 **New {game_info['name']} Code Found!** 🚨\n\n"
            f"**Code:** `{code}`\n"
            f"**Rewards:** {rewards}{link_line}"
        ),
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except requests.RequestException as e:
        print(f"Discord alert failed for {code}: {e}")


def scrape_fandom_wiki(game_key, game_info, known_codes):
    found_entries = []
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        resp = requests.get(game_info["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[{game_key}] Failed to fetch {game_info['url']}: {e}")
        return found_entries

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table", class_="wikitable")

    for table in tables:
        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            row_text = row.get_text(" ", strip=True).lower()
            is_expired = "expired" in row_text and "valid" not in row_text

            # Extract codes from <code> tags in the first cell
            code_tags = cells[0].find_all("code")
            if not code_tags:
                continue

            # Rewards are usually in cell 2 (or cell 1 depending on wiki layout)
            rewards_text = cells[2].get_text(" ", strip=True) if len(cells) >= 3 else "In-game rewards"
            rewards_text = re.sub(r"\s+", " ", rewards_text)[:140]

            is_permanent = "permanent" in row_text or "indefinite" in row_text

            for tag in code_tags:
                code = tag.get_text(strip=True)
                if not re.match(r"^[A-Za-z0-9]{5,24}$", code):
                    continue

                entry = {
                    "game": game_key,
                    "code": code,
                    "rewards": rewards_text,
                    "expiresAt": "2020-01-01T00:00:00Z" if is_expired else None,
                    "addedAt": today_str,
                    "permanent": is_permanent,
                }
                found_entries.append(entry)

                # Notify Discord only for brand-new, active codes
                if not is_expired and code not in known_codes:
                    print(f"[{game_key}] New active code: {code}")
                    send_discord_alert(game_info, code, rewards_text)
                    known_codes.add(code)

    return found_entries


def main():
    print("Scanning all 4 games for redeem codes...")
    known_codes = get_known_codes()
    all_codes = []

    for game_key, game_info in GAMES.items():
        entries = scrape_fandom_wiki(game_key, game_info, known_codes)
        print(f"[{game_key}] Parsed {len(entries)} codes.")
        all_codes.extend(entries)

    # Deduplicate by (game, code)
    unique = {}
    for item in all_codes:
        unique[(item["game"], item["code"])] = item

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "codes": list(unique.values()),
    }

    with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    save_known_codes(known_codes)
    print(f"Done. Wrote {len(output['codes'])} codes to {OUTPUT_JSON_FILE}.")


if __name__ == "__main__":
    main()
