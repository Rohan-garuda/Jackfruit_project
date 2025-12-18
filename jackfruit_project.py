import customtkinter as ctk
from datetime import datetime, timedelta, time
import pytz
import pygame
from astral import LocationInfo
from astral.sun import sun
from tkcalendar import Calendar
import holidays
import json
import winsound
import os
import threading
from tkinter import messagebox


CITIES = {
    "Mumbai": {"region": "Asia/Kolkata", "coords": (19.0760, 72.8777), "country": "IN"},
    "New York": {"region": "America/New_York", "coords": (40.7128, -74.0060), "country": "US"},
    "London": {"region": "Europe/London", "coords": (51.5074, -0.1278), "country": "GB"},
    "Tokyo": {"region": "Asia/Tokyo", "coords": (35.6762, 139.6503), "country": "JP"},
    "Beijing": {"region": "Asia/Shanghai", "coords": (39.9042, 116.4074), "country": "CN"},
    "Sydney": {"region": "Australia/Sydney", "coords": (-33.8688, 151.2093), "country": "AU"},
    "Dubai": {"region": "Asia/Dubai", "coords": (25.2048, 55.2708), "country": "AE"},
    "Paris": {"region": "Europe/Paris", "coords": (48.8566, 2.3522), "country": "FR"},
    "Moscow": {"region": "Europe/Moscow", "coords": (55.7558, 37.6173), "country": "RU"},
    "Los Angeles": {"region": "America/Los_Angeles", "coords": (34.0522, -118.2437), "country": "US"},
    "Singapore": {"region": "Asia/Singapore", "coords": (1.3521, 103.8198), "country": "SG"},
    "Rio de Janeiro": {"region": "America/Sao_Paulo", "coords": (-22.9068, -43.1729), "country": "BR"},
    "Berlin": {"region": "Europe/Berlin", "coords": (52.5200, 13.4050), "country": "DE"},
    "Rome": {"region": "Europe/Rome", "coords": (41.9028, 12.4964), "country": "IT"},
    "Madrid": {"region": "Europe/Madrid", "coords": (40.4168, -3.7038), "country": "ES"},
    "Amsterdam": {"region": "Europe/Amsterdam", "coords": (52.3676, 4.9041), "country": "NL"},
    "Zurich": {"region": "Europe/Zurich", "coords": (47.3769, 8.5417), "country": "CH"},
    "Lisbon": {"region": "Europe/Lisbon", "coords": (38.7223, -9.1393), "country": "PT"},
    "Melbourne": {"region": "Australia/Melbourne", "coords": (-37.8136, 144.9631), "country": "AU"},
    "Canberra": {"region": "Australia/Canberra", "coords": (-35.2809, 149.1300), "country": "AU"}
}

DB_FILE = "meetings_db_mytime.json"

class WorldClockApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Global Solar Scheduler Ultimate")
        self.geometry("1200x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=0) 
        self.grid_rowconfigure(0, weight=1)
        self.clock_frame = ctk.CTkScrollableFrame(self, label_text="Live World Status")
        self.clock_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.city_cards = {} 
        for city_name in CITIES:
            card = self.create_city_card(self.clock_frame, city_name)
            card.pack(pady=8, padx=10, fill="x")

       
        self.right_panel = ctk.CTkTabview(self, width=450)
        self.right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.tab_planner = self.right_panel.add("Plan & Schedule")
        self.tab_meetings = self.right_panel.add("My Meetings")

        self.create_planner_ui()
        self.create_meetings_list_ui()
        
        self.load_global_holidays()
        self.meetings_data = self.load_meetings_from_db()
        self.refresh_meeting_list()

        self.update_clocks()
        self.check_alarms()
        self.stop_audio_flag = False

    def create_city_card(self, parent, city_name):
        card = ctk.CTkFrame(parent)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text=city_name, font=("Arial", 16, "bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        label_time = ctk.CTkLabel(card, text="--:--", font=("Courier New", 24, "bold"), text_color="#3B8ED0")
        label_time.grid(row=0, column=1, padx=10, sticky="e")
        label_info = ctk.CTkLabel(card, text="Loading...", font=("Arial", 11), text_color="gray")
        label_info.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")
        
        self.city_cards[city_name] = {"time": label_time, "info": label_info}
        return card

    def create_planner_ui(self):
        ctk.CTkLabel(self.tab_planner, text="1. Select Date:", text_color="gray").pack(anchor="w", padx=10)
        
        self.cal = Calendar(self.tab_planner, selectmode='day', 
                            background='black', foreground='white', 
                            headersbackground='#3B8ED0', normalbackground='#333333', 
                            normalforeground='white', selectbackground='#1F6AA5') 

        self.cal.pack(pady=5)
        
        self.cal.pack(pady=5)
        self.cal.tag_config('holiday', background='#E74C3C', foreground='white')
        self.cal.bind("<<CalendarSelected>>", self.check_holiday_on_click)
        self.lbl_holiday_info = ctk.CTkLabel(self.tab_planner, text="Select date to check holidays", text_color="#E74C3C", font=("Arial", 11))
        self.lbl_holiday_info.pack(pady=(0, 5))

        
        ctk.CTkLabel(self.tab_planner, text="2. Meeting Details:", text_color="gray").pack(anchor="w", padx=10)
        
        loc_frame = ctk.CTkFrame(self.tab_planner, fg_color="transparent")
        loc_frame.pack(pady=5, padx=10, fill="x")

        
        ctk.CTkLabel(loc_frame, text="My City:").grid(row=0, column=0, padx=5, sticky="e")
        self.my_city_var = ctk.StringVar(value="Mumbai")
        ctk.CTkOptionMenu(loc_frame, values=list(CITIES.keys()), variable=self.my_city_var, width=120).grid(row=0, column=1, padx=5)

       
        ctk.CTkLabel(loc_frame, text="Client City:").grid(row=1, column=0, padx=5, sticky="e", pady=5)
        self.client_city_var = ctk.StringVar(value="New York")
        ctk.CTkOptionMenu(loc_frame, values=list(CITIES.keys()), variable=self.client_city_var, width=120).grid(row=1, column=1, padx=5, pady=5)

        
        time_frame = ctk.CTkFrame(self.tab_planner, fg_color="transparent")
        time_frame.pack(pady=5)
        ctk.CTkLabel(time_frame, text="My Time: ").pack(side="left") 
        self.hour_entry = ctk.CTkEntry(time_frame, placeholder_text="HH", width=40)
        self.hour_entry.pack(side="left", padx=2)
        ctk.CTkLabel(time_frame, text=":").pack(side="left")
        self.minute_entry = ctk.CTkEntry(time_frame, placeholder_text="MM", width=40)
        self.minute_entry.pack(side="left", padx=2)

        self.title_entry = ctk.CTkEntry(self.tab_planner, placeholder_text="Meeting Title (e.g. Project Sync)")
        self.title_entry.pack(pady=5, padx=10, fill="x")

        btn_frame = ctk.CTkFrame(self.tab_planner, fg_color="transparent")
        btn_frame.pack(pady=10, fill="x", padx=10)
        ctk.CTkButton(btn_frame, text="Check Converted Time", command=self.calculate_conversion, fg_color="#2CC985").pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(btn_frame, text="Save to My Meetings", command=self.save_meeting, fg_color="#3B8ED0").pack(side="right", padx=5, expand=True, fill="x")

      
        self.results_textbox = ctk.CTkTextbox(self.tab_planner, height=100)
        self.results_textbox.pack(pady=10, padx=10, fill="both", expand=True)

    def create_meetings_list_ui(self):
        self.meetings_frame = ctk.CTkScrollableFrame(self.tab_meetings, label_text="My Schedule")
        self.meetings_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def load_meetings_from_db(self):
        if not os.path.exists(DB_FILE): return []
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return []

    def save_meetings_to_db(self):
        with open(DB_FILE, "w") as f: json.dump(self.meetings_data, f)

    def get_meeting_times(self):
        date_str = self.cal.get_date()
        my_city = self.my_city_var.get()
        client_city = self.client_city_var.get()
        
        try:
            h = int(self.hour_entry.get())
            m = int(self.minute_entry.get()) if self.minute_entry.get() else 0
            
            my_tz = pytz.timezone(CITIES[my_city]["region"])
            dt_naive = datetime.strptime(date_str, "%m/%d/%y").replace(hour=h, minute=m)
            dt_my = my_tz.localize(dt_naive)
            client_tz = pytz.timezone(CITIES[client_city]["region"])
            dt_client = dt_my.astimezone(client_tz)
            return dt_my, dt_client, my_city, client_city
            
        except ValueError:
            return None, None, None, None

    def calculate_conversion(self):
        dt_my, dt_client, my_city, client_city = self.get_meeting_times()
        if not dt_my:
            self.results_textbox.delete("0.0", "end")
            self.results_textbox.insert("0.0", "Error: Invalid Time.")
            return

        h = dt_client.hour
        status_icon = "✅"  
        status_msg = "(Good Time)"
        
        if h < 8 or h >= 20: 
            status_icon = "❌"
            status_msg = "(Night/Sleep)"
        elif h < 9 or h >= 18:
            status_icon = "⚠️"
            status_msg = "(Stretch)"

        report = f"--- Time Conversion ---\n"
        report += f"🏠 YOU ({my_city}): {dt_my.strftime('%I:%M %p')}\n"
        report += f"📍 Client ({client_city}): {dt_client.strftime('%I:%M %p')} {status_icon}\n"
        report += f"   Status: {status_msg}"
        
        self.results_textbox.delete("0.0", "end")
        self.results_textbox.insert("0.0", report)

    def save_meeting(self):
        title = self.title_entry.get()
        if not title:
            messagebox.showerror("Error", "Please enter a Meeting Title!")
            return

        dt_my, dt_client, my_city, client_city = self.get_meeting_times()
        if not dt_my:
            messagebox.showerror("Error", "Invalid Time format.")
            return

        new_meeting = {
            "title": title,
            "iso_time_trigger": dt_my.isoformat(),
            "date_display": dt_my.strftime("%d %b %Y"), 
            "my_time_str": dt_my.strftime("%I:%M %p"),
            "client_time_str": dt_client.strftime("%I:%M %p"),
            "my_city": my_city,
            "client_city": client_city,
            "alerted": False
        }
        
        self.meetings_data.append(new_meeting)
        self.save_meetings_to_db()
        self.refresh_meeting_list()
        self.results_textbox.delete("0.0", "end")
        messagebox.showinfo("Success", "Meeting Saved!")

    def refresh_meeting_list(self):
        for widget in self.meetings_frame.winfo_children(): widget.destroy()
        self.meetings_data.sort(key=lambda x: x["iso_time_trigger"])

        for i, meeting in enumerate(self.meetings_data):
            row = ctk.CTkFrame(self.meetings_frame)
            row.pack(fill="x", pady=5)
            
            header_frame = ctk.CTkFrame(row, fg_color="transparent")
            header_frame.pack(fill="x", padx=10, pady=(5,0))
            
            ctk.CTkLabel(header_frame, text=meeting['date_display'], font=("Arial", 14, "bold"), text_color="#3B8ED0").pack(side="left")
            ctk.CTkLabel(header_frame, text=f"| {meeting['title']}", font=("Arial", 12, "bold"), text_color="white").pack(side="left", padx=10)

            my_txt = f"🏠 My Time ({meeting['my_city']}):  {meeting['my_time_str']}"
            ctk.CTkLabel(row, text=my_txt, font=("Courier New", 12), text_color="#2CC985").pack(anchor="w", padx=10, pady=(2,0))
            
            client_txt = f"📍 Client ({meeting['client_city']}): {meeting['client_time_str']}"
            ctk.CTkLabel(row, text=client_txt, font=("Courier New", 12)).pack(anchor="w", padx=10, pady=(0,5))
            
            ctk.CTkButton(row, text="Del", width=40, fg_color="#E74C3C", height=20,
                          command=lambda idx=i: self.delete_meeting(idx)).pack(anchor="e", padx=10, pady=(0,5))

    def delete_meeting(self, index):
        del self.meetings_data[index]
        self.save_meetings_to_db()
        self.refresh_meeting_list()

    def check_alarms(self):
        now_utc = datetime.now(pytz.utc)
        for meeting in self.meetings_data:
            if not meeting["alerted"]:
                trigger_dt = datetime.fromisoformat(meeting["iso_time_trigger"])
                if 0 <= (now_utc - trigger_dt).total_seconds() < 60:
                    threading.Thread(target=self.play_ringtone).start()
                    msg = (f"MEETING ALERT!\n\nTitle: {meeting['title']}\n"
                           f"Start Now: {meeting['my_time_str']}")
                    messagebox.showwarning("ALARM", msg)
                    try:
                        import pygame
                        pygame.mixer.music.stop()
                    except:
                        pass

                    meeting["alerted"] = True
                    self.save_meetings_to_db()

        self.after(1000, self.check_alarms)

    def play_ringtone(self):
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load("ringtone.mp3") 
            pygame.mixer.music.play(-1) 
        except Exception as e:
            print(f"Audio Error: {e}")

    def load_global_holidays(self):
        current_year = datetime.now().year
        years = [current_year, current_year + 1]
        processed_countries = set()
        for city, data in CITIES.items():
            country_code = data["country"]
            if country_code in processed_countries: continue
            country_holidays = holidays.country_holidays(country_code, years=years)
            for date, name in country_holidays.items():
                self.cal.calevent_create(date, f"{name}", "holiday")
            processed_countries.add(country_code)

    def check_holiday_on_click(self, event):
        date_str = self.cal.get_date()
        try:
            selected_date = datetime.strptime(date_str, "%m/%d/%y").date()
            found_holidays = []
            checked_countries = set()
            for city, data in CITIES.items():
                c_code = data["country"]
                if c_code in checked_countries: continue
                hols = holidays.country_holidays(c_code)
                holiday_name = hols.get(selected_date)
                if holiday_name: found_holidays.append(f"• {holiday_name} ({c_code})")
                checked_countries.add(c_code)
            if found_holidays: self.lbl_holiday_info.configure(text="\n".join(found_holidays), text_color="#E74C3C")
            else: self.lbl_holiday_info.configure(text="No International Holidays Found", text_color="gray")
        except: pass

    def get_city_details(self, city_name, dt_city_time):
        data = CITIES[city_name]
        city_info = LocationInfo(city_name, "", data["region"], data["coords"][0], data["coords"][1])
        s = sun(city_info.observer, date=dt_city_time)
        sunrise = s['sunrise'].astimezone(pytz.timezone(data["region"])).strftime('%H:%M')
        sunset = s['sunset'].astimezone(pytz.timezone(data["region"])).strftime('%H:%M')
        dst_delta = dt_city_time.dst()
        dst_amount = dst_delta.total_seconds() / 3600
        dst_status = f"DST +{int(dst_amount)}h" if dst_amount > 0 else "Std Time"
        return f"☀ Rise: {sunrise} Set: {sunset}  |  ℹ {dst_status}"

    def update_clocks(self):
        utc_now = datetime.now(pytz.utc)
        for city, widgets in self.city_cards.items():
            tz = pytz.timezone(CITIES[city]["region"])
            city_time = utc_now.astimezone(tz)
            widgets["time"].configure(text=city_time.strftime("%I:%M %p"))
            info_text = self.get_city_details(city, city_time)
            widgets["info"].configure(text=info_text)
        self.after(1000, self.update_clocks)

if __name__ == "__main__":
    app = WorldClockApp()
    app.mainloop()