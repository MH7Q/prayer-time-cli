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

# --- IMPORT YOUR MODULES ---
import config
import api
import utils
import languages
import startup

APP_VERSION = "0.6"
BG_COLOR = "#0f0f0f"
CARD_COLOR = "#1a1a1a"
TEXT_MAIN = "#ffffff"
TEXT_DIM = "#888888"
ACCENT_CYAN = "#00E5FF"
ACCENT_GOLD = "#FFD700"
ACCENT_RED = "#FF1744"

class PrayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Prayer Station v{APP_VERSION}")
        self.root.geometry("450x800")
        self.root.configure(bg=BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        self.cfg = config.load_config()
        # Default 24h if not set
        if 'time_format' not in self.cfg: self.cfg['time_format'] = "24h"
        
        self.timings = {}
        self.mini_win = None
        self.settings_win = None
        
        utils.init_audio()
        self.setup_ui()
        self.apply_lang()
        
        threading.Thread(target=self.setup_tray, daemon=True).start()
        threading.Thread(target=self.data_loop, daemon=True).start()
        self.root.after(1000, self.clock_loop)

    def setup_ui(self):
        self.header = tk.Frame(self.root, bg=BG_COLOR)
        self.header.pack(pady=20, fill="x", padx=20)
        
        self.btn_hud = tk.Button(self.header, text="🖥️", bg=BG_COLOR, fg=ACCENT_CYAN, font=("Arial", 14), bd=0, command=self.toggle_mini_mode)
        self.btn_hud.pack(side="left")

        self.btn_sets = tk.Button(self.header, text="⚙️", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 14), bd=0, command=self.open_settings)
        self.btn_sets.pack(side="right")
        
        self.lbl_title = tk.Label(self.header, text="SALAH TIMES", font=("Impact", 28), bg=BG_COLOR, fg=TEXT_MAIN)
        self.lbl_title.pack()

        self.lbl_loc = tk.Label(self.root, text=self.cfg.get('city', 'Detecting...'), font=("Arial", 10), bg=BG_COLOR, fg=TEXT_DIM)
        self.lbl_loc.pack()
        
        self.lbl_next = tk.Label(self.root, text="...", font=("Verdana", 10, "bold"), bg=BG_COLOR, fg=ACCENT_CYAN)
        self.lbl_next.pack(pady=(10, 0))
        
        self.lbl_timer = tk.Label(self.root, text="00:00:00", font=("Courier New", 44, "bold"), bg=BG_COLOR, fg=ACCENT_RED)
        self.lbl_timer.pack()

        self.card = tk.Frame(self.root, bg=CARD_COLOR, padx=20, pady=20)
        self.card.pack(pady=20, padx=20, fill="x")
        
        self.p_widgets = {}
        for p in ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            row = tk.Frame(self.card, bg=CARD_COLOR)
            row.pack(fill='x', pady=6)
            lbl_n = tk.Label(row, text=p, font=("Arial", 12), bg=CARD_COLOR, fg=TEXT_MAIN)
            lbl_t = tk.Label(row, text="--:--", font=("Arial", 12, "bold"), bg=CARD_COLOR, fg=TEXT_DIM)
            self.p_widgets[p] = (lbl_n, lbl_t, row)

        tk.Label(self.root, text="Coded by MH7Q 🇸🇦", font=("Arial", 9, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(side="bottom", pady=20)

    # --- SETTINGS WITH 12/24H TOGGLE ---
    def open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift(); return
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("Settings")
        self.settings_win.geometry("400x650")
        self.settings_win.configure(bg=CARD_COLOR)
        self.settings_win.grab_set()

        # Language selection
        tk.Label(self.settings_win, text="Language:", bg=CARD_COLOR, fg="white").pack(pady=(10,0))
        lang_var = tk.StringVar(value=self.cfg.get('lang', 'en'))
        lang_cb = ttk.Combobox(self.settings_win, textvariable=lang_var, values=list(languages.LANG_DATA.keys()), state="readonly")
        lang_cb.pack(pady=5)

        # Time Format selection (New!)
        tk.Label(self.settings_win, text="Time Format:", bg=CARD_COLOR, fg="white").pack(pady=(10,0))
        format_var = tk.StringVar(value=self.cfg.get('time_format', '24h'))
        format_cb = ttk.Combobox(self.settings_win, textvariable=format_var, values=["12h", "24h"], state="readonly")
        format_cb.pack(pady=5)

        # City entry
        tk.Label(self.settings_win, text="City:", bg=CARD_COLOR, fg="white").pack(pady=(10,0))
        ent_city = tk.Entry(self.settings_win, font=("Arial", 12), bg="#333", fg="white", bd=0)
        ent_city.pack(pady=5, padx=20, fill="x")
        ent_city.insert(0, self.cfg.get('city', ''))

        def auto_detect_click():
            detected = api.get_current_location()
            ent_city.delete(0, tk.END)
            ent_city.insert(0, detected)
            messagebox.showinfo("Location", f"Detected: {detected}")

        tk.Button(self.settings_win, text="📍 Find My Location", bg="#444", fg=ACCENT_CYAN, command=auto_detect_click).pack(pady=10)

        def save():
            self.cfg['lang'] = lang_var.get()
            self.cfg['city'] = ent_city.get()
            self.cfg['time_format'] = format_var.get()
            config.save_config(self.cfg)
            self.lbl_loc.config(text=self.cfg['city'])
            self.apply_lang()
            threading.Thread(target=self.fetch_data, daemon=True).start()
            self.settings_win.destroy()
            
        tk.Button(self.settings_win, text="SAVE", bg=ACCENT_CYAN, font=("Arial", 11, "bold"), command=save).pack(pady=20)

    # --- CORE LOGIC ---
    def data_loop(self):
        while True:
            self.fetch_data()
            time.sleep(3600)

    def fetch_data(self):
        data = api.fetch_prayer_times(self.cfg.get('city', 'Riyadh'))
        if data:
            self.timings = data['timings']
            self.root.after(0, self.refresh_times)

    def refresh_times(self):
        fmt = self.cfg.get('time_format', '24h')
        for p, (lbl_n, lbl_t, row) in self.p_widgets.items():
            if p in self.timings:
                t_str = self.timings[p][:5]
                if fmt == "12h":
                    t_obj = datetime.strptime(t_str, "%H:%M")
                    t_str = t_obj.strftime("%I:%M %p")
                lbl_t.config(text=t_str)

    def clock_loop(self):
        now = datetime.now()
        if self.timings: self.update_countdown(now)
        if self.mini_win and self.mini_win.winfo_exists():
            self.mini_lbl.config(text=self.lbl_timer.cget("text"))
        self.root.after(1000, self.clock_loop)

    def update_countdown(self, now):
        next_p = None; min_sec = 999999
        l_code = self.cfg.get('lang', 'en')
        d = languages.LANG_DATA.get(l_code, languages.LANG_DATA['en'])
        
        for p in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if p not in self.timings: continue
            p_dt = now.replace(hour=int(self.timings[p][:2]), minute=int(self.timings[p][3:5]), second=0)
            if p_dt > now:
                diff = (p_dt - now).total_seconds()
                if diff < min_sec: min_sec = diff; next_p = p
        
        if not next_p: # Next is tomorrow's Fajr
            next_p = 'Fajr'
            p_dt = (now + timedelta(days=1)).replace(hour=int(self.timings['Fajr'][:2]), minute=int(self.timings['Fajr'][3:5]), second=0)
            min_sec = (p_dt - now).total_seconds()

        h, m, s = int(min_sec//3600), int((min_sec%3600)//60), int(min_sec%60)
        translated_p = utils.fix_text(d['prayers'][next_p], l_code)
        self.lbl_next.config(text=f"{translated_p.upper()}")
        self.lbl_timer.config(text=f"{h:02}:{m:02}:{s:02}")

    # (Add your standard apply_lang, toggle_mini_mode, setup_tray, etc. here)
    def apply_lang(self):
        l_code = self.cfg.get('lang', 'en')
        d = languages.LANG_DATA.get(l_code, languages.LANG_DATA['en'])
        is_rtl = d.get('dir') == 'rtl'
        self.lbl_title.config(text=utils.fix_text(d['title'], l_code))
        self.btn_hud.pack_forget(); self.btn_sets.pack_forget()
        if is_rtl:
            self.btn_hud.pack(side="right"); self.btn_sets.pack(side="left")
        else:
            self.btn_hud.pack(side="left"); self.btn_sets.pack(side="right")
        for p, (lbl_n, lbl_t, row) in self.p_widgets.items():
            lbl_n.pack_forget(); lbl_t.pack_forget()
            lbl_n.config(text=utils.fix_text(d['prayers'][p], l_code))
            if is_rtl: lbl_n.pack(side="right"); lbl_t.pack(side="left")
            else: lbl_n.pack(side="left"); lbl_t.pack(side="right")

    def toggle_mini_mode(self):
        if self.mini_win and self.mini_win.winfo_exists(): self.mini_win.destroy(); return
        self.mini_win = tk.Toplevel(self.root)
        self.mini_win.overrideredirect(True)
        self.mini_win.attributes("-topmost", True, "-alpha", 0.8)
        self.mini_win.geometry("160x50+30+30")
        self.mini_win.configure(bg=CARD_COLOR)
        self.mini_lbl = tk.Label(self.mini_win, text="--:--:--", fg=ACCENT_CYAN, bg=CARD_COLOR, font=("Courier New", 14, "bold"))
        self.mini_lbl.pack(expand=True)
        def start_move(e): self.x, self.y = e.x, e.y
        def on_move(e):
            nx = self.mini_win.winfo_x() + (e.x - self.x)
            ny = self.mini_win.winfo_y() + (e.y - self.y)
            self.mini_win.geometry(f"+{nx}+{ny}")
        self.mini_win.bind("<Button-1>", start_move); self.mini_win.bind("<B1-Motion>", on_move)

    def setup_tray(self):
        img = Image.new('RGB', (64, 64), (15,15,15))
        d = ImageDraw.Draw(img); d.ellipse((10,10,54,54), fill=(0, 230, 118))
        self.icon = pystray.Icon("PrayerStation", img, "Prayer Station", (pystray.MenuItem('Show', lambda: self.root.after(0, self.root.deiconify())), pystray.MenuItem('Quit', lambda: os._exit(0))))
        self.icon.run()

    def minimize_to_tray(self): self.root.withdraw()

if __name__ == "__main__":
    root = tk.Tk()
    app = PrayerApp(root)
    root.mainloop()