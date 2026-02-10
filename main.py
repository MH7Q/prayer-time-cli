import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import threading
from datetime import datetime, timedelta
import pystray
from PIL import Image, ImageDraw
import sys
import time
import os
import locale
import arabic_reshaper
from bidi.algorithm import get_display

# --- IMPORT MODULES ---
import config
import api
import utils
import languages
import startup

APP_VERSION = "0.4"
BG_COLOR = "#0f0f0f"
CARD_COLOR = "#1a1a1a"
TEXT_MAIN = "#ffffff"
TEXT_DIM = "#888888"
ACCENT_CYAN = "#00E5FF"
ACCENT_GOLD = "#FFD700"
ACCENT_RED = "#FF1744"

# EXPANDED CITY LIST
CITIES_LIST = [
    "Mecca, Saudi Arabia", "Medina, Saudi Arabia", "Riyadh, Saudi Arabia", "Jeddah, Saudi Arabia",
    "Dubai, UAE", "Abu Dhabi, UAE", "Cairo, Egypt", "Alexandria, Egypt",
    "London, UK", "Manchester, UK", "Birmingham, UK",
    "New York, USA", "Los Angeles, USA", "Chicago, USA", "Houston, USA",
    "Paris, France", "Marseille, France", "Lyon, France",
    "Berlin, Germany", "Munich, Germany", "Frankfurt, Germany",
    "Istanbul, Turkey", "Ankara, Turkey", "Jakarta, Indonesia",
    "Kuala Lumpur, Malaysia", "Dhaka, Bangladesh", "Karachi, Pakistan",
    "Mumbai, India", "New Delhi, India", "Toronto, Canada", "Sydney, Australia",
    "Moscow, Russia", "Tokyo, Japan"
]

class PrayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Prayer Station v{APP_VERSION}")
        self.root.geometry("450x800")
        self.root.configure(bg=BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Load Config
        self.cfg = config.load_config()
        if 'lang' not in self.cfg or self.cfg['lang'] not in languages.LANG_DATA:
            self.cfg['lang'] = self.detect_system_lang()
        if 'startup' not in self.cfg:
            self.cfg['startup'] = False
            
        self.timings = {}
        self.icon = None
        self.settings_win = None
        self.remote_version = None
        
        utils.init_audio()
        
        # Build UI Directly (No Splash)
        self.setup_ui()
        
        # Apply Startup Setting
        startup.set_startup(self.cfg['startup'])

        # Start Threads
        threading.Thread(target=self.setup_tray, daemon=True).start()
        threading.Thread(target=self.data_loop, daemon=True).start()
        threading.Thread(target=self.version_check_loop, daemon=True).start()
        self.root.after(1000, self.clock_loop)

    def detect_system_lang(self):
        try:
            sys_lang = locale.getdefaultlocale()[0]
            if sys_lang:
                for lang in ["ar", "fr", "id", "ur"]:
                    if lang in sys_lang: return lang
        except: pass
        return "en"

    # --- MAIN UI ---
    def setup_ui(self):
        self.header = tk.Frame(self.root, bg=BG_COLOR)
        self.header.pack(pady=20, fill="x", padx=20)
        
        self.btn_sets = tk.Button(self.header, text="⚙️", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 14), bd=0, command=self.open_settings)
        self.lbl_title = tk.Label(self.header, text="SALAH TIMES", font=("Impact", 28), bg=BG_COLOR, fg=TEXT_MAIN)
        
        self.lbl_loc = tk.Label(self.root, text=self.cfg['city'], font=("Arial", 10), bg=BG_COLOR, fg=TEXT_DIM, wraplength=400)
        self.lbl_loc.pack()
        self.lbl_date = tk.Label(self.root, text="...", font=("Arial", 11, "bold"), bg=BG_COLOR, fg=TEXT_MAIN)
        self.lbl_date.pack(pady=(0,15))
        
        self.lbl_next = tk.Label(self.root, text="...", font=("Verdana", 10, "bold"), bg=BG_COLOR, fg=ACCENT_CYAN)
        self.lbl_next.pack()
        self.lbl_timer = tk.Label(self.root, text="--:--:--", font=("Courier New", 44, "bold"), bg=BG_COLOR, fg=ACCENT_RED)
        self.lbl_timer.pack()
        self.btn_stop = tk.Button(self.root, text="STOP", bg=ACCENT_RED, fg="white", bd=0, command=self.stop_sound)
        
        self.card = tk.Frame(self.root, bg=CARD_COLOR, padx=20, pady=20)
        self.card.pack(pady=20, padx=20, fill="x")
        
        self.p_widgets = {}
        for p in ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            row = tk.Frame(self.card, bg=CARD_COLOR)
            row.pack(fill='x', pady=6)
            lbl_n = tk.Label(row, text=p, font=("Arial", 12), bg=CARD_COLOR, fg=TEXT_MAIN)
            lbl_t = tk.Label(row, text="--:--", font=("Arial", 12, "bold"), bg=CARD_COLOR, fg=TEXT_DIM)
            self.p_widgets[p] = (lbl_n, lbl_t, row)

        # FOOTER
        self.footer = tk.Frame(self.root, bg=BG_COLOR)
        self.footer.pack(side="bottom", fill="x", pady=10, padx=10)
        
        # Mismatch Button (Left)
        self.btn_update = tk.Button(self.footer, text="⚠️ Update", bg=BG_COLOR, fg=ACCENT_GOLD, font=("Arial", 9, "bold"), bd=0, cursor="hand2", command=self.open_github)
        
        # Version (Right)
        self.lbl_ver = tk.Label(self.footer, text=f"v{APP_VERSION}", font=("Arial", 8), bg=BG_COLOR, fg="#444")
        self.lbl_ver.pack(side="right")

        # --- SIGNATURE (Center Bottom) ---
        tk.Label(self.root, text="Coded by MH7Q 🇸🇦", font=("Arial", 9, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(side="bottom", pady=(0, 5))

        self.apply_lang()

    # --- SETTINGS MENU ---
    def open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift(); return
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("Settings")
        self.settings_win.geometry("380x650")
        self.settings_win.configure(bg=CARD_COLOR)
        
        d = languages.LANG_DATA[self.cfg['lang']]

        # --- DONATION BUTTON ---
        def open_dono():
            webbrowser.open("https://www.buymeacoffee.com/MH7Q")
            
        tk.Button(self.settings_win, text="☕ Support Developer", bg="#FFDD00", fg="black", font=("Arial", 10, "bold"), bd=0, cursor="hand2", command=open_dono).pack(pady=(20, 10))

        # 1. CITY
        tk.Label(self.settings_win, text=utils.fix_text(d['city'], self.cfg['lang']), bg=CARD_COLOR, fg="white", font=("Arial", 10, "bold")).pack(pady=(15,5))
        ent_city = tk.Entry(self.settings_win, font=("Arial", 12), bg="#333", fg="white", insertbackground="white")
        ent_city.pack(pady=5, padx=20, fill="x")
        ent_city.insert(0, self.cfg['city'])
        lst_city = tk.Listbox(self.settings_win, font=("Arial", 10), bg="#222", fg="white", height=4, bd=0, highlightthickness=0)
        lst_city.pack(pady=0, padx=20, fill="x")
        for c in CITIES_LIST: lst_city.insert(tk.END, c)
        
        def update_city(e):
            t = ent_city.get().lower(); lst_city.delete(0,tk.END)
            for c in CITIES_LIST: 
                if t in c.lower(): lst_city.insert(tk.END, c)
        def select_city(e):
            if lst_city.curselection(): ent_city.delete(0,tk.END); ent_city.insert(0, lst_city.get(lst_city.curselection()))
        ent_city.bind('<KeyRelease>', update_city); lst_city.bind('<<ListboxSelect>>', select_city)

        # 2. LANGUAGE
        tk.Label(self.settings_win, text=utils.fix_text(d['lang_sel'], self.cfg['lang']), bg=CARD_COLOR, fg="white", font=("Arial", 10, "bold")).pack(pady=(15,5))
        
        display_to_code = {}
        all_display_names = []
        current_display = "English"
        for name, code in languages.LANG_MAP_RAW.items():
            reshaped = name
            if code in ['ar', 'ur']: reshaped = get_display(arabic_reshaper.reshape(name))
            all_display_names.append(reshaped)
            display_to_code[reshaped] = code
            if code == self.cfg['lang']: current_display = reshaped

        ent_lang = tk.Entry(self.settings_win, font=("Arial", 12), bg="#333", fg="white", insertbackground="white")
        ent_lang.pack(pady=5, padx=20, fill="x")
        ent_lang.insert(0, current_display)
        lst_lang = tk.Listbox(self.settings_win, font=("Arial", 10), bg="#222", fg="white", height=4, bd=0, highlightthickness=0)
        lst_lang.pack(pady=0, padx=20, fill="x")
        for l in all_display_names: lst_lang.insert(tk.END, l)

        def update_lang(e):
            t = ent_lang.get().lower(); lst_lang.delete(0,tk.END)
            for l in all_display_names: 
                if t in l.lower(): lst_lang.insert(tk.END, l)
        def select_lang(e):
            if lst_lang.curselection(): ent_lang.delete(0,tk.END); ent_lang.insert(0, lst_lang.get(lst_lang.curselection()))
        ent_lang.bind('<KeyRelease>', update_lang); lst_lang.bind('<<ListboxSelect>>', select_lang)

        # 3. STARTUP
        startup_var = tk.BooleanVar(value=self.cfg.get('startup', False))
        startup_txt = utils.fix_text(d['startup'], self.cfg['lang'])
        chk_startup = tk.Checkbutton(self.settings_win, text=startup_txt, variable=startup_var, 
                                     bg=CARD_COLOR, fg="white", selectcolor=BG_COLOR, activebackground=CARD_COLOR, activeforeground="white", font=("Arial", 10))
        chk_startup.pack(pady=20)

        # SAVE
        def save():
            self.cfg['city'] = ent_city.get()
            self.cfg['lang'] = display_to_code.get(ent_lang.get(), "en")
            self.cfg['startup'] = startup_var.get()
            startup.set_startup(self.cfg['startup'])
            config.save_config(self.cfg)
            self.lbl_loc.config(text=self.cfg['city'])
            self.apply_lang()
            threading.Thread(target=self.fetch_data, daemon=True).start()
            self.settings_win.destroy()

        tk.Button(self.settings_win, text=utils.fix_text(d['save'], self.cfg['lang']), bg=ACCENT_CYAN, font=("Arial", 11, "bold"), command=save).pack(pady=10, fill="x", padx=40)

    # --- LANG ENGINE ---
    def apply_lang(self):
        l = self.cfg['lang']; d = languages.LANG_DATA[l]; direction = d['dir']
        
        self.btn_sets.pack_forget(); self.lbl_title.pack_forget()
        if self.remote_version:
             msg = f"{d['mismatch']}{self.remote_version}"
             self.btn_update.config(text=utils.fix_text(msg, l))
             self.btn_update.pack(side="left") # Show update button only if needed

        if direction == 'rtl':
            self.btn_sets.pack(side="left", padx=5)
            self.lbl_title.config(text=utils.fix_text(d['title'], l))
            self.lbl_title.pack(side="right")
        else:
            self.btn_sets.pack(side="right", padx=5)
            self.lbl_title.config(text=d['title'])
            self.lbl_title.pack(side="left")

        for p, (lbl_n, lbl_t, row) in self.p_widgets.items():
            lbl_n.pack_forget(); lbl_t.pack_forget()
            lbl_n.config(text=utils.fix_text(d['prayers'][p], l))
            if direction == 'rtl': lbl_n.pack(side="right"); lbl_t.pack(side="left")
            else: lbl_n.pack(side="left"); lbl_t.pack(side="right")

    # --- CORE ---
    def fetch_data(self):
        data = api.fetch_prayer_times(self.cfg['city'])
        if data:
            self.timings = data['timings']
            self.root.after(0, self.refresh_times)

    def data_loop(self):
        while True:
            self.fetch_data(); time.sleep(3600)

    def version_check_loop(self):
        self.check_version()
        while True: time.sleep(1800); self.check_version()

    def check_version(self):
        remote = api.check_version_mismatch(APP_VERSION)
        if remote:
            self.remote_version = remote
            self.root.after(0, self.show_mismatch_alert)

    def show_mismatch_alert(self):
        d = languages.LANG_DATA[self.cfg['lang']]
        msg = f"{d['mismatch']}{self.remote_version}"
        self.btn_update.config(text=utils.fix_text(msg, self.cfg['lang']))
        self.btn_update.pack(side="left")

    def clock_loop(self):
        now = datetime.now()
        if self.timings:
            self.calc_countdown(now)
            if now.second == 0:
                cur = now.strftime("%H:%M")
                for p in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
                    if cur == self.timings.get(p, "")[:5]: utils.play_adhan()
        
        if utils.is_audio_playing(): self.btn_stop.pack(pady=5, after=self.lbl_timer)
        else: self.btn_stop.pack_forget()
        self.root.after(1000, self.clock_loop)

    def stop_sound(self): utils.stop_audio()
    def open_github(self): webbrowser.open("https://github.com/MH7Q/prayer-time-cli")

    def calc_countdown(self, now):
        next_p = None; min_sec = 999999
        for p in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if p not in self.timings: continue
            p_time = datetime.strptime(self.timings[p][:5], "%H:%M")
            p_date = now.replace(hour=p_time.hour, minute=p_time.minute, second=0)
            if p_date > now:
                diff = (p_date - now).total_seconds(); 
                if diff < min_sec: min_sec = diff; next_p = p
        
        if not next_p and 'Fajr' in self.timings:
            next_p = "Fajr"
            f_time = datetime.strptime(self.timings['Fajr'][:5], "%H:%M")
            p_date = (now + timedelta(days=1)).replace(hour=f_time.hour, minute=f_time.minute, second=0)
            min_sec = (p_date - now).total_seconds()

        if next_p:
            hours = int(min_sec // 3600); mins = int((min_sec % 3600) // 60); secs = int(min_sec % 60)
            self.lbl_next.config(text=f"NEXT: {next_p.upper()}")
            self.lbl_timer.config(text=f"{hours:02}:{mins:02}:{secs:02}")

    def refresh_times(self):
        for p, (lbl_n, lbl_t, row) in self.p_widgets.items():
            if p in self.timings:
                t = self.timings[p][:5]
                t_obj = datetime.strptime(t, "%H:%M")
                lbl_t.config(text=t_obj.strftime("%I:%M %p"))

    def setup_tray(self):
        image = Image.new('RGB', (64, 64), color=(15, 15, 15))
        d = ImageDraw.Draw(image); d.ellipse((10,10,54,54), fill=(0, 230, 118))
        menu = (pystray.MenuItem('Show', self.show_window), pystray.MenuItem('Quit', self.quit_app))
        self.icon = pystray.Icon("PrayerStation", image, "Prayer Station", menu)
        self.icon.run()
    def minimize_to_tray(self): self.root.withdraw()
    def show_window(self, icon, item): self.root.after(0, self.root.deiconify)
    def quit_app(self, icon, item): self.icon.stop(); self.root.quit(); sys.exit()

if __name__ == "__main__":
    root = tk.Tk()
    app = PrayerApp(root)
    root.mainloop()
