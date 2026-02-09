import requests
import json
import os
import time
import threading
from datetime import datetime, date, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from plyer import notification

# --- Configuration ---
CONFIG_FILE = "config.json"
GREEN = "#00ff41"  
DARK = "#0d0d0d"   
TEXT_COLOR = "#ffffff"

class PrayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MH7Q Prayer Tool")
        self.root.geometry("400x600") # Made slightly taller for update button
        self.root.configure(bg=DARK)
        self.root.resizable(False, False)

        # --- Version Control ---
        self.current_version = "0.1"
        # Make sure these URLs are "Raw" links or valid text files
        self.github_version_url = "https://raw.githubusercontent.com/MH7Q/prayer-time-cli/main/version.txt"
        self.github_repo_url = "https://github.com/MH7Q/prayer-time-cli"

        # --- Data Variables ---
        self.timings = {}
        self.next_prayer_name = "Wait..."
        self.time_left = "Loading..."
        self.city = "Riyadh"  # Default
        self.country = "Saudi Arabia"
        self.last_fetch_date = None

        # --- UI Setup ---
        self.setup_ui()
        
        # --- Start ---
        self.load_config()
        
        # 1. Start Data Fetch (Background)
        threading.Thread(target=self.fetch_data_thread, daemon=True).start()
        
        # 2. Start Update Check (Background)
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        
        # 3. Start GUI Loop
        self.root.after(1000, self.gui_loop)

    def setup_ui(self):
        # Header
        header = tk.Label(self.root, text="MH7Q PRAYER TOOL", font=("Courier", 20, "bold"), bg=DARK, fg=GREEN)
        header.pack(pady=20)

        # Next Prayer Box
        self.lbl_next = tk.Label(self.root, text="NEXT: ...", font=("Arial", 14), bg=DARK, fg=TEXT_COLOR)
        self.lbl_next.pack()
        
        self.lbl_timer = tk.Label(self.root, text="--:--:--", font=("Arial", 35, "bold"), bg=DARK, fg="red")
        self.lbl_timer.pack(pady=10)

        # Prayer List Frame
        self.frame_list = tk.Frame(self.root, bg=DARK)
        self.frame_list.pack(pady=20)
        
        self.prayer_labels = {}
        prayers = ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
        
        for p in prayers:
            row = tk.Frame(self.frame_list, bg=DARK)
            row.pack(fill='x', pady=2)
            
            lbl_name = tk.Label(row, text=p, font=("Courier", 12), bg=DARK, fg=TEXT_COLOR, width=10, anchor='w')
            lbl_name.pack(side='left', padx=20)
            
            lbl_time = tk.Label(row, text="--:--", font=("Courier", 12, "bold"), bg=DARK, fg=GREEN, width=10, anchor='e')
            lbl_time.pack(side='right', padx=20)
            
            self.prayer_labels[p] = lbl_time

        # Status Bar
        self.lbl_status = tk.Label(self.root, text="Starting...", font=("Arial", 9), bg=DARK, fg="gray")
        self.lbl_status.pack(side='bottom', pady=10)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if 'address' in data:
                        self.city = data['address'].split(',')[0]
            except: pass

    def fetch_data_thread(self):
        """Runs in background so GUI doesn't freeze"""
        while True:
            today_str = date.today().strftime("%d-%m-%Y")
            if self.last_fetch_date != today_str:
                self.update_status("Downloading data...")
                url = f"http://api.aladhan.com/v1/timingsByCity/{today_str}?city={self.city}&country={self.country}&method=4"
                
                try:
                    response = requests.get(url, timeout=10)
                    data = response.json()
                    
                    if response.status_code == 200:
                        self.timings = data['data']['timings']
                        self.last_fetch_date = today_str
                        self.root.after(0, self.update_prayer_list_ui)
                        self.update_status(f"Location: {self.city}")
                    else:
                        self.update_status("API Error. Retrying...")
                        time.sleep(10)
                        
                except Exception as e:
                    self.update_status("Connection Failed. Retrying...")
                    time.sleep(10)
            
            time.sleep(3600)

    def update_status(self, text):
        self.root.after(0, lambda: self.lbl_status.config(text=text))

    def update_prayer_list_ui(self):
        for p, lbl in self.prayer_labels.items():
            if p in self.timings:
                t_24 = self.timings[p][:5]
                t_obj = datetime.strptime(t_24, "%H:%M")
                t_12 = t_obj.strftime("%I:%M %p")
                lbl.config(text=t_12)

    def gui_loop(self):
        """Runs every 1 second to update the countdown"""
        if self.timings:
            now = datetime.now()
            self.update_countdown(now)
            
            if now.second == 0:
                 current_time_str = now.strftime("%H:%M")
                 for p_name in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
                     if current_time_str == self.timings[p_name][:5]:
                         self.send_notification(p_name)

        self.root.after(1000, self.gui_loop)

    def update_countdown(self, now):
        next_p = None
        min_diff = 999999
        
        for p_name in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if p_name not in self.timings: continue
            
            p_time_str = self.timings[p_name][:5]
            p_time = datetime.strptime(p_time_str, "%H:%M")
            p_date = now.replace(hour=p_time.hour, minute=p_time.minute, second=0)
            
            if p_date > now:
                diff = (p_date - now).total_seconds()
                if diff < min_diff:
                    min_diff = diff
                    next_p = p_name

        if next_p is None and 'Fajr' in self.timings:
            next_p = "Fajr (Tomorrow)"
            fajr_str = self.timings['Fajr'][:5]
            f_time = datetime.strptime(fajr_str, "%H:%M")
            tomorrow = now + timedelta(days=1)
            f_date = tomorrow.replace(hour=f_time.hour, minute=f_time.minute, second=0)
            min_diff = (f_date - now).total_seconds()

        if next_p:
            hours = int(min_diff // 3600)
            minutes = int((min_diff % 3600) // 60)
            seconds = int(min_diff % 60)
            
            self.lbl_next.config(text=f"NEXT: {next_p.upper()}")
            self.lbl_timer.config(text=f"{hours:02}:{minutes:02}:{seconds:02}")

    def send_notification(self, prayer_name):
        try:
            notification.notify(
                title=f"It is time for {prayer_name}",
                message=f"Time to pray {prayer_name}!",
                app_name="MH7Q Prayer Tool",
                timeout=10
            )
        except: pass

    # --- UPDATE LOGIC ---
    def check_for_updates(self):
        """Checks GitHub for a newer version"""
        try:
            response = requests.get(self.github_version_url, timeout=3)
            if response.status_code == 200:
                # Strip whitespace to avoid mismatch (e.g., "0.2\n" vs "0.2")
                latest_version = response.text.strip()
                
                # Simple string comparison (works for 0.1 vs 0.2)
                if latest_version > self.current_version:
                    self.root.after(0, lambda: self.show_update_button(latest_version))
        except:
            pass 

    def show_update_button(self, new_ver):
        btn = tk.Button(self.root, text=f"🚀 UPDATE AVAILABLE ({new_ver})", bg="blue", fg="white", font=("Arial", 10, "bold"),
                        command=self.open_github)
        # Pack it before the status bar so it appears at the bottom
        btn.pack(pady=5, side='bottom', before=self.lbl_status)

    def open_github(self):
        webbrowser.open(self.github_repo_url)

if __name__ == "__main__":
    root = tk.Tk()
    app = PrayerApp(root)
    root.mainloop()