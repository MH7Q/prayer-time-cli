import requests
from datetime import date

def fetch_prayer_times(city):
    today = date.today().strftime("%d-%m-%Y")
    # Auto-detects method based on location
    url = f"http://api.aladhan.com/v1/timingsByAddress?address={city}&date={today}"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()['data']
    except Exception as e:
        print(f"API Error: {e}")
    return None

def check_version_mismatch(current_version):
    # Reads the raw version.txt from GitHub
    url = "https://raw.githubusercontent.com/MH7Q/prayer-time-cli/refs/heads/main/version.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            remote_ver = res.text.strip()
            # STRICT CHECK: If they are NOT the same, return the remote version
            if remote_ver != current_version and len(remote_ver) < 10:
                return remote_ver
    except Exception as e:
        print(f"Update Check Error: {e}")
    return None