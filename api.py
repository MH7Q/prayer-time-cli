import requests
from datetime import date
import geocoder

def get_current_location():
    try:
        # Detects location based on IP
        g = geocoder.ip('me')
        if g.city and g.country:
            return f"{g.city}, {g.country}"
    except:
        pass
    return "Riyadh, Saudi Arabia"

def fetch_prayer_times(city):
    today = date.today().strftime("%d-%m-%Y")
    url = f"http://api.aladhan.com/v1/timingsByAddress?address={city}&date={today}"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()['data']
    except Exception as e:
        print(f"API Error: {e}")
    return None

def check_version_mismatch(current_version):
    url = "https://raw.githubusercontent.com/MH7Q/prayer-time-cli/refs/heads/main/version.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            remote_ver = res.text.strip()
            if remote_ver != current_version and len(remote_ver) < 10:
                return remote_ver
    except:
        pass
    return None