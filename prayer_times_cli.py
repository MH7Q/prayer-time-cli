import requests
import json
import argparse
import os
import sys
from datetime import datetime, date, timedelta


# --- Configuration ---
CONFIG_FILE = "config.json"

# --- Visuals ---
BANNER = r"""
    __  __ __  __ _____  ____ 
   /  |/  / / / //__  / / __ \
  / /|_/ / /_/ /   / / / / / /
 / /  / / __  /   / / / /_/ / 
/_/  /_/_/ /_/   /_/  \___\_\ 
"""
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

TEXTS = {
    "en": {
        "app_name": "PRAYER TIME CLI",
        "welcome": "Welcome to MH7Q Prayer Tool",
        "loc_prompt": "📍 Enter Location (e.g., Riyadh, London): ",
        "loading": "Fetching data for",
        "error_loc": "❌ Error: Could not find that location.",
        "error_conn": "❌ Connection Error: Check your internet.",
        "next_prayer": "NEXT PRAYER",
        "time_left": "TIME LEFT",
        "saved_loc": "📍 Using saved location:",
        "tomorrow": "Tomorrow",
        "month_gen": "📅 Generating Monthly Schedule...",
        "month_done": "✅ Saved schedule to:",
        "qibla": "Qibla Direction",
        "gregorian": "Gregorian",
        "hijri": "Hijri",
        "timezone": "Timezone",
        "fajr": "Fajr",
        "sunrise": "Sunrise",
        "dhuhr": "Dhuhr",
        "asr": "Asr",
        "maghrib": "Maghrib",
        "isha": "Isha"
    },
    "ar": {
        "app_name": "أداة أوقات الصلاة",
        "welcome": "أهلاً بك في أداة MH7Q للصلاة",
        "loc_prompt": "📍 أدخل الموقع (مثال: Riyadh, Dubai): ",
        "loading": "جاري جلب البيانات لـ",
        "error_loc": "❌ خطأ: لم يتم العثور على الموقع.",
        "error_conn": "❌ خطأ في الاتصال: تأكد من الإنترنت.",
        "next_prayer": "الصلاة القادمة",
        "time_left": "الوقت المتبقي",
        "saved_loc": "📍 الموقع المحفوظ:",
        "tomorrow": "غداً",
        "month_gen": "📅 جاري إنشاء جدول الشهر...",
        "month_done": "✅ تم حفظ الجدول في:",
        "qibla": "اتجاه القبلة",
        "gregorian": "ميلادي",
        "hijri": "هجري",
        "timezone": "المنطقة الزمنية",
        "fajr": "الفجر",
        "sunrise": "الشروق",
        "dhuhr": "الظهر",
        "asr": "العصر",
        "maghrib": "المغرب",
        "isha": "العشاء"
    }
}

def convert_to_12h(time_24):
    try:
        clean_time = time_24[:5]
        time_obj = datetime.strptime(clean_time, "%H:%M")
        return time_obj.strftime("%I:%M %p")
    except:
        return time_24

def generate_monthly_schedule(address, lang_code):
    print(f"\n{YELLOW}{TEXTS[lang_code]['month_gen']}{RESET}")
    today = date.today()
    url = f"http://api.aladhan.com/v1/calendarByAddress/{today.year}/{today.month}"
    params = {'address': address, 'method': 4}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        filename = f"Schedule_{address.replace(' ', '_')}_{today.month}_{today.year}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Prayer Schedule for {address}\n")
            f.write("="*65 + "\n")
            f.write(f"{'Date':<12} | {'Fajr':<9} | {'Dhuhr':<9} | {'Asr':<9} | {'Maghrib':<9} | {'Isha':<9}\n")
            f.write("="*65 + "\n")
            for day in data['data']:
                d = day['date']['gregorian']['date']
                t = day['timings']
                f.write(f"{d:<12} | {convert_to_12h(t['Fajr']):<9} | {convert_to_12h(t['Dhuhr']):<9} | {convert_to_12h(t['Asr']):<9} | {convert_to_12h(t['Maghrib']):<9} | {convert_to_12h(t['Isha']):<9}\n")
        print(f"{GREEN}{TEXTS[lang_code]['month_done']} {filename}{RESET}\n")
    except Exception as e: print(f"{RED}Error: {e}{RESET}")

def get_next_prayer(timings, lang_code):
    now = datetime.now()
    prayer_map_display = {
        'Fajr': TEXTS[lang_code]['fajr'],
        'Dhuhr': TEXTS[lang_code]['dhuhr'],
        'Asr': TEXTS[lang_code]['asr'],
        'Maghrib': TEXTS[lang_code]['maghrib'],
        'Isha': TEXTS[lang_code]['isha']
    }
    
    for p_eng in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
        if p_eng not in timings: continue
        p_time = datetime.strptime(timings[p_eng][:5], "%H:%M")
        p_time_today = now.replace(hour=p_time.hour, minute=p_time.minute, second=0)
        
        if p_time_today > now:
            delta = p_time_today - now
            return prayer_map_display[p_eng], str(delta).split('.')[0], p_eng

    fajr_time = datetime.strptime(timings['Fajr'][:5], "%H:%M")
    tomorrow = datetime.now() + timedelta(days=1)
    fajr_tomorrow = tomorrow.replace(hour=fajr_time.hour, minute=fajr_time.minute, second=0)
    delta = fajr_tomorrow - now
    tomorrow_txt = TEXTS[lang_code]['tomorrow']
    return f"{prayer_map_display['Fajr']} ({tomorrow_txt})", str(delta).split('.')[0], 'Fajr'

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return None
    return None

def save_config(address, lang):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump({"address": address, "lang": lang}, f, ensure_ascii=False)

def get_prayer_times():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-a', '--address', type=str)
    parser.add_argument('-l', '--lang', type=str, choices=['en', 'ar'])
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--month', action='store_true')
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
        print(f"{GREEN}Settings reset.{RESET}")
        return

    config = load_config()
    address, lang = None, None

    if args.lang: lang = args.lang
    elif config and 'lang' in config: lang = config['lang']
    else:
        print(GREEN + BANNER + RESET)
        print("1. English")
        print("2. العربية (Arabic)")
        choice = input(f"{BOLD}Choose Language / اختر اللغة (1/2): {RESET}").strip()
        lang = 'ar' if choice == '2' else 'en'

    T = TEXTS[lang]

    if args.address:
        address = args.address
        save_config(address, lang)
    elif config and 'address' in config:
        address = config['address']
        if not args.month:
            print(GREEN + BANNER + RESET)
            print(f"{YELLOW}{T['saved_loc']} {address}{RESET}")
    else:
        if not args.lang: print(GREEN + BANNER + RESET)
        print(f"{BOLD}{T['welcome']}{RESET}\n")
        address = input(T['loc_prompt']).strip()
        save_config(address, lang)

    if args.month:
        generate_monthly_schedule(address, lang)
        return

    today = date.today().strftime("%d-%m-%Y")
    url = f"http://api.aladhan.com/v1/timingsByAddress/{today}"
    params = {'address': address, 'method': 4}

    print(f"\n🔄 {GREEN}{T['loading']} {address}...{RESET}")

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200 and data['code'] == 200:
            timings = data['data']['timings']
            meta = data['data']['meta']
            date_hijri = data['data']['date']['hijri']
            next_p_display, time_left, next_p_key = get_next_prayer(timings, lang)

            print("\n" + "="*45)
            print(f"📅 {T['gregorian']}: {today}")
            print(f"🌙 {T['hijri']}:     {date_hijri['day']} {date_hijri['month']['en']} {date_hijri['year']}")
            qibla_dir = data['data']['meta'].get('qibla_direction', 'N/A')
            print(f"🧭 {T['qibla']}:     {qibla_dir}°")
            print(f"📍 {T['timezone']}:  {meta['timezone']}")
            print("="*45)
            
            def p_row(key, val):
                # Lookup translations using lower case key, e.g., 'fajr'
                lbl = T.get(key.lower(), key)
                time_str = convert_to_12h(val)
                if key == next_p_key:
                    print(f"{CYAN}{BOLD}➜ {lbl:<10} \t{time_str}  <--{RESET}")
                else:
                    print(f"  {lbl:<10} \t{time_str}")

            p_row('Fajr', timings['Fajr'])
            p_row('Sunrise', timings['Sunrise'])
            p_row('Dhuhr', timings['Dhuhr'])
            p_row('Asr', timings['Asr'])
            p_row('Maghrib', timings['Maghrib'])
            p_row('Isha', timings['Isha'])
            print("="*45)

            print(f"\n🚀 {BOLD}{T['next_prayer']}: {CYAN}{next_p_display}{RESET}")
            print(f"⏳ {BOLD}{T['time_left']}:   {RED}{time_left}{RESET}")
            print("="*45 + "\n")
            
        else:
            print(f"\n{T['error_loc']}")
            if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)

    except Exception as e:
        # Print the actual error for debugging
        print(f"\n{T['error_conn']} {e}")

if __name__ == "__main__":
    get_prayer_times()
