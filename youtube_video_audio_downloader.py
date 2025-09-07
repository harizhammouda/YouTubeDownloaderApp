import ctypes
ctypes.windll.user32.SetProcessDPIAware()
import customtkinter as ctk
from tkinter import filedialog
import tkinter as tk
import os
import subprocess
import threading
import time
import webbrowser
import pyperclip
import sys
import re
import requests
import win11toast
import uuid
import gspread
import os.path
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from yt_dlp import YoutubeDL
from tkinter import messagebox
from PIL import Image, ImageTk
# إعداد ملف السجل في مجلد AppData
log_file_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "YouTubeDownloader", "debug_log.txt")
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

# إعادة تعيين ملف السجل عند بدء التطبيق
if os.path.exists(log_file_path):
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write(f"{time.ctime()}: Log file reset on application start.\n")

def log_message(message):
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()}: {message}\n")


def sanitize_filename(filename):
    """Remove invalid characters and keep Arabic, Latin, numbers, dashes, dots, and spaces."""
    # السماح بالأحرف العربية، اللاتينية، الأرقام، الشرطات، النقاط، والمسافات
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)  # إزالة الأحرف غير القانونية في ويندوز
    filename = re.sub(r'\s+', ' ', filename).strip()  # استبدال المسافات المتعددة بمسافة واحدة
    return filename
def display_image_centered(image_path):
    root = tk.Toplevel()
    root.attributes('-topmost', True)
    root.overrideredirect(True)

    # تحديث النافذة قبل حساب الإحداثيات
    root.update_idletasks()

    image = Image.open(image_path)
    image = image.resize((400, 400), Image.LANCZOS)
    photo = ImageTk.PhotoImage(image)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 400) // 2
    y = (screen_height - 400) // 2
    root.geometry(f"400x400+{x}+{y}")

    label = tk.Label(root, image=photo, borderwidth=0, highlightthickness=0)
    label.pack()

    root.attributes('-transparentcolor', 'black')
    label.configure(bg='black')

    label.image = photo

    root.after(5000, root.destroy)

class YouTubeDownloaderApp:
    CURRENT_VERSION = "3.9"  # الإصدار الحالي

    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader 3.9")
        exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        display_image_centered(os.path.join(exe_dir, "img", "splash.png"))


        # حساب الموقع لتوسيط النافذة
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 700) // 2
        y = (screen_height - 600) // 2 - 50
        self.root.geometry(f"700x600+{x}+{y}")
        self.root.resizable(False, False)

        self.root.attributes('-topmost', False)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")




        icon_path = os.path.join(exe_dir, "img", "download.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.is_downloading = False
        self.downloaded_file = None
        self.download_process = None
        self.info_dict = None
        self.is_paste_active = False

        self.settings_file = os.path.join(os.path.dirname(log_file_path), "settings.txt")
        self.user_stats_file = os.path.join(os.path.dirname(log_file_path), "user_stats.txt")
        self.notifications_enabled = tk.BooleanVar(value=True)
        self.tooltip_enabled = tk.BooleanVar(value=True)
        self.load_settings()

        # فحص التحديث في خيط خلفي
        import threading
        import queue
        update_queue = queue.Queue()
        update_thread = threading.Thread(target=self.check_for_update, args=(update_queue,))
        update_thread.start()

        # انتظر 5 ثواني فقط
        update_thread.join(timeout=5)

        # إذا انتهى الخيط، اعرض النافذة فورًا
        if not update_queue.empty():
            self.show_update_prompt(update_queue.get())

        # عرض الواجهة الرئيسية فورًا
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # إذا كان الخيط لا يزال يعمل، راقب الـ queue كل 100ms لعرض النافذة إذا وجد تحديث
        if update_thread.is_alive():
            def check_queue():
                if not update_queue.empty():
                    self.show_update_prompt(update_queue.get())
                else:
                    self.root.after(100, check_queue)

            self.root.after(100, check_queue)

        # التحقق من الفتح الأول
        if not self.is_first_run_checked():
            import webbrowser
            index_path = os.path.join(exe_dir, "index", "index.html")
            if os.path.exists(index_path):
                webbrowser.open(f"file://{index_path}")
            self.mark_first_run()
            self.is_first_run_checked()  # إعادة قراءة user_id بعد إنشاء user_stats.txt
        if self.user_id:  # إرسال الإحصائيات فقط إذا وجد user_id
            self.send_stats_to_sheets()

    def check_for_update(self, update_queue):
        log_message("Starting update check...")
        try:
            document_id = '1z2eTuv56ntlW0edEozYkPNagEnEIbgbWzhOYjBL6aW4'
            export_url = f'https://docs.google.com/document/d/{document_id}/export?format=txt'

            response = requests.get(export_url)
            if response.status_code == 200:
                full_text = response.text
                log_message("Fetched public Google Docs content via export URL.")

                version_match = re.search(r'Latest Version: (\d+\.\d+)', full_text)
                size_match = re.search(r'Size: ([\d.]+[MB|GB])', full_text)
                link_match = re.search(r'Download Link: (https?://[^\s]+)', full_text)

                latest_version = version_match.group(1) if version_match else None
                size = size_match.group(1) if size_match else "Unknown"
                download_link = link_match.group(1) if link_match else "No link provided"

                if latest_version and float(latest_version) > float(self.CURRENT_VERSION):
                    log_message(f"Found update: Version={latest_version}, Size={size}, Link={download_link}")
                    update_queue.put((latest_version, size, download_link))
                else:
                    log_message("No update needed or version not found.")
            else:
                log_message(f"Failed to fetch export URL: status {response.status_code}")

        except Exception as e:
            log_message(f"Update check failed (no internet?): {e}")

    def show_update_prompt(self, update_data):
        latest_version, size, download_link = update_data
        response_msg = messagebox.askyesno(
            "Update Required",
            f"Current version {self.CURRENT_VERSION}: Download feature from YouTube is not working. You must download the new version.\nA new version ({latest_version}, {size}) is available. Update is required for downloads to work properly. Continue?",
            parent=self.root
        )
        log_message(f"User response: {'Continue' if response_msg else 'No'}")
        if response_msg:
            # نافذة مخصصة للتعليمات مع رابط قابل للنقر
            instructions_window = ctk.CTkToplevel(self.root)
            instructions_window.attributes('-topmost', True)  # إضافة هذا السطر هنا لجعلها في المقدمة
            instructions_window.title("Update Instructions")
            instructions_window.geometry("370x200")
            instructions_window.resizable(False, False)
            instructions_window.grab_set()  # إجبارية

            # توسيط النافذة في الشاشة
            def center_window():
                instructions_window.update_idletasks()
                screen_width = instructions_window.winfo_screenwidth()
                screen_height = instructions_window.winfo_screenheight()
                win_width = instructions_window.winfo_width()
                win_height = instructions_window.winfo_height()
                x = (screen_width - win_width) // 2
                y = (screen_height - win_height) // 2 - 50
                instructions_window.geometry(f"{win_width}x{win_height}+{x}+{y}")

            instructions_window.after(100, center_window)

            # إغلاق عند X
            instructions_window.protocol("WM_DELETE_WINDOW",
                                         lambda: [instructions_window.destroy(), self.root.destroy()])

            # تعيين الأيقونة مع دعم exe (استخدم sys._MEIPASS إذا مبني)
            import sys
            if getattr(sys, 'frozen', False):
                exe_dir = sys._MEIPASS
                log_message("Running as exe, using _MEIPASS for icon path.")
            else:
                exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
                log_message("Running as script, using realpath for icon path.")

            icon_path = os.path.join(exe_dir, "img", "download.ico")
            if os.path.exists(icon_path):
                instructions_window.after(200, lambda: instructions_window.iconbitmap(icon_path))
                log_message(f"Icon path exists: {icon_path} - Setting icon.")
            else:
                log_message(f"Icon path does not exist: {icon_path} - Skipping icon.")

            title_label = ctk.CTkLabel(instructions_window, text="How to get the new version, here are the steps.",
                                       font=("Arial", 16))
            title_label.pack(pady=10)

            step1_label = ctk.CTkLabel(instructions_window,
                                       text=f"1. First, delete this version {self.CURRENT_VERSION} completely from your device.",
                                       font=("Arial", 14), wraplength=400)
            step1_label.pack(pady=5)

            step2_label = ctk.CTkLabel(instructions_window,
                                       text=f"2. Click on the link to download the new version {latest_version} then install it.",
                                       font=("Arial", 14), wraplength=400)
            step2_label.pack(pady=5)

            link_label = ctk.CTkLabel(instructions_window, text="Click here", text_color="#00FF00",
                                      font=("Arial", 14, "underline"), cursor="hand2")
            link_label.pack(pady=5)
            link_label.bind("<Button-1>", lambda e: webbrowser.open(download_link))

            thanks_label = ctk.CTkLabel(instructions_window, text="And thanks.", font=("Arial", 14))
            thanks_label.pack(pady=5)

            ok_button = ctk.CTkButton(instructions_window, text="OK",
                                      command=lambda: [instructions_window.destroy(), self.root.destroy()])
            ok_button.pack(pady=10)

            log_message("Showed update instructions.")

    def is_first_run_checked(self):
        # التحقق مما إذا كان التطبيق قد فُتح من قبل
        try:
            with open(self.user_stats_file, "r", encoding="utf-8-sig") as f:
                raw_content = f.read()
                log_message(f"Full raw content of user_stats file: '{raw_content}'")
            # إعادة فتح الملف لقراءة الأسطر
            with open(self.user_stats_file, "r", encoding="utf-8-sig") as f:
                settings = {}
                line_number = 0
                raw_lines = f.readlines()
                log_message(f"Raw lines read from user_stats: {raw_lines}")
                for line in raw_lines:
                    line_number += 1
                    line = line.strip()
                    log_message(f"Processing line {line_number}: '{line}'")
                    if line and "=" in line and len(line.split("=", 1)) == 2:
                        key, value = line.split("=", 1)
                        settings[key] = value.strip()
                    else:
                        log_message(f"Skipped invalid or empty line {line_number}: '{line}'")
                log_message(f"Parsed user_stats: {settings}")
                self.user_id = settings.get("user_id", "")
                log_message(f"Read user_id from user_stats: {self.user_id}")
                return settings.get("first_run", "False") == "True"
        except FileNotFoundError:
            self.user_id = ""
            log_message("User_stats file not found, user_id set to empty")
            return False

    def mark_first_run(self):
        # وضع علامة أن التطبيق فُتح لأول مرة
        user_id = uuid.uuid4().hex  # توليد معرف فريد
        stats = {"first_run": "True", "user_id": user_id}
        with open(self.user_stats_file, "w", encoding="utf-8") as f:
            for key, value in stats.items():
                f.write(f"{key}={value}\n")
        log_message(f"Wrote user_stats: {stats}")

    def send_stats_to_sheets(self):
        if not self.user_id:  # إذا لم يوجد user_id، تجاهل
            log_message("No user_id found, skipping stats.")
            return

        def send_in_background():
            try:
                # إعداد الاتصال بـ Google Sheets
                scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
                client = gspread.authorize(creds)
                sheet = client.open("YouTubeDownloader_Stats").sheet1
                # إرسال البيانات
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([self.user_id, "3.9", timestamp])
                log_message(f"Sent stats to Google Sheets: user_id={self.user_id}, version=3.9")
            except Exception as e:
                log_message(f"Failed to send stats to Google Sheets: {str(e)}")

        # إرسال في خيط خلفي
        threading.Thread(target=send_in_background).start()


    def create_widgets(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.welcome_label = ctk.CTkLabel(title_frame, text="Welcome to YouTube Downloader",
                                          font=("Arial", 20, "bold"))
        self.welcome_label.pack(pady=5)
        self.version_label = ctk.CTkLabel(title_frame, text="Version 3.9",
                                          text_color="gray", font=("Arial", 15))
        self.version_label.pack()
        title_frame.pack(fill="x")

        self.notebook = ctk.CTkTabview(self.main_frame)
        self.download_tab = self.notebook.add("Download")
        self.about_tab = self.notebook.add("About")
        self.contribute_tab = self.notebook.add("Contribute")
        self.update_tab = self.notebook.add("Update")
        self.notebook.pack(fill="both", expand=True, pady=10)

        self.setup_download_tab()
        self.setup_about_tab()
        self.setup_contribute_tab()

        # إضافة محتوى التحديث من الملف الجديد
        from update_checker import create_update_content
        update_content = create_update_content(self.update_tab)
        update_content.pack(fill="both", expand=True)

    def setup_download_tab(self):

        self.url_label = ctk.CTkLabel(self.download_tab, text="Video URL:", font=("Arial", 15))

        self.url_label.pack(anchor="w", pady=1)


        refresh_image = ctk.CTkImage(light_image=Image.open("img/img2.png"), size=(11, 11))
        self.reset_button = ctk.CTkButton(self.download_tab, image=refresh_image, text="", width=17, height=17,
                                          fg_color="#333333", corner_radius=8,
                                          # تقليل corner_radius لتناسب الحجم الأصغر
                                          command=self.reset_app)
        self.reset_button.place(x=620, y=0)
        self.create_tooltip(self.reset_button,
                            "Click to reset the app for a \n new video link or to fix errors.")


        self.url_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.url_entry = ctk.CTkEntry(self.url_frame, width=400, height=28, font=("Arial", 13),
                                      placeholder_text="Put video link here .URL", placeholder_text_color="gray")

        self.url_entry.pack(side="left", padx=(15, 3))


        self.clear_url_button = ctk.CTkButton(self.url_frame, text="X", width=17, height=17, font=("Arial", 10),
                                              fg_color="#333333", hover_color="#4d4d4d", corner_radius=8,
                                              command=lambda: self.url_entry.delete(0, "end"))
        self.clear_url_button.place(relx=1.0, x=-32, y=5)

        self.url_frame.pack(pady=3, padx=(3, 12))


        self.paste_button = ctk.CTkButton(self.download_tab, text="Paste",
                                          command=self.paste_from_clipboard, width=84, height=28, font=("Arial", 13))

        self.paste_button.pack(pady=3)


        self.separator = ctk.CTkFrame(self.download_tab, height=2, width=490, fg_color="gray50", corner_radius=5)

        self.separator.pack(anchor="center", pady=6)


        self.video_title_label = ctk.CTkLabel(self.download_tab, text="Video Title: No video selected",
                                              font=("Arial", 15), wraplength=700, justify="center")

        self.video_title_label.pack(anchor="center", pady=1)


        self.progress = ctk.CTkProgressBar(self.download_tab, width=280)
        self.progress.set(0)

        self.progress.pack(pady=6)
        self.progress.pack_forget()

        self.progress_label = ctk.CTkLabel(self.download_tab, text="", font=("Arial", 15))

        self.progress_label.pack(pady=1)
        self.progress_label.pack_forget()

        self.merge_label = ctk.CTkLabel(self.download_tab, text="", font=("Arial", 15))
        self.merge_label.pack(pady=1)
        self.merge_label.pack_forget()


        self.file_path_label = ctk.CTkLabel(self.download_tab, text="Save to:", font=("Arial", 15))
        self.file_path_label.pack(anchor="w", pady=1)


        self.output_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.output_entry = ctk.CTkEntry(self.output_frame, width=245, height=28, font=("Arial", 13),
                                         placeholder_text="Select the save path here.", placeholder_text_color="gray")

        self.output_entry.pack(side="left", padx=3)
        self.output_entry.configure(state="disabled")

        self.browse_button = ctk.CTkButton(self.output_frame, text="Browse",
                                           command=self.browse_folder, width=84, height=28, font=("Arial", 13),
                                           state="disabled")
        self.browse_button.pack(side="left")

        self.output_frame.pack(pady=3, anchor="center")


        self.file_type_label = ctk.CTkLabel(self.download_tab, text="File Type:", font=("Arial", 15))
        self.file_type_label.pack(anchor="w", pady=1)

        self.type_var = ctk.StringVar(value="choose")
        self.type_var.trace("w", self.update_type)


        self.type_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.type_frame.pack(anchor="center", pady=3, padx=(19, 0))


        self.type_menu = ctk.CTkOptionMenu(
            self.type_frame,
            values=["choose", "mp3     (Audio, Classic)", "OPUS   (Audio, Faster & Smaller)", "mp4     (Video)"],
            variable=self.type_var,
            width=210,
            height=28,
            font=("Arial", 13)
        )
        self.type_menu.configure(state="disabled")

        self.type_menu.pack(side="left", padx=(0, 3))


        self.help_button = ctk.CTkButton(
            master=self.type_frame,
            text="?",
            width=14,
            height=10,
            corner_radius=8,
            fg_color="#424242",
            hover_color="#303030",
            font=("Arial", 13, "bold"),
            command=self.open_help_page
        )
        self.help_button.pack(side="left")


        self.quality_label = ctk.CTkLabel(self.download_tab, text="Quality:", font=("Arial", 15))
        self.quality_label.pack(anchor="w", pady=1)

        self.quality_var = ctk.StringVar(value="choose")
        self.quality_var.trace("w", self.update_quality)

        self.quality_menu = ctk.CTkOptionMenu(self.download_tab, values=["choose"], variable=self.quality_var,
                                              width=210, height=28, font=("Arial", 13))
        self.quality_menu.configure(state="disabled")

        self.quality_menu.pack(pady=3)


        self.download_button = ctk.CTkButton(self.download_tab, text="Download",
                                             command=self.start_download, width=105, height=28, font=("Arial", 13),
                                             state="disabled")

        self.download_button.pack(pady=12)

    def open_help_page(self):
        """
        فتح ملف index.html في المتصفح مع التمرير إلى قسم OPUS vs MP3.
        """
        help_file_path = os.path.join(os.path.dirname(__file__), "index", "index.html")
        if os.path.exists(help_file_path):
            webbrowser.open(f"file://{os.path.abspath(help_file_path)}#opus-mp3")
            log_message(f"Opened help page: {help_file_path}")
        else:
            log_message(f"Help file not found: {help_file_path}")
            self.progress_label.configure(text="Error: Help file not found")
            self.root.update()
            time.sleep(3)
            self.progress_label.configure(text="")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("notifications="):
                        self.notifications_enabled.set(int(line.split("=")[1]) == 1)
                    elif line.startswith("tooltip="):
                        self.tooltip_enabled.set(int(line.split("=")[1]) == 1)
        else:
            self.save_settings()  # إنشاء الملف بقيم افتراضية

    def save_settings(self):
        with open(self.settings_file, "w") as f:
            f.write(f"notifications={1 if self.notifications_enabled.get() else 0}\n")
            f.write(f"tooltip={1 if self.tooltip_enabled.get() else 0}\n")

    def setup_about_tab(self):

        about_frame = ctk.CTkFrame(self.about_tab, fg_color="transparent")
        about_frame.pack(pady=15, padx=15, fill="both", expand=True)


        self.thanks_label = ctk.CTkLabel(about_frame, text="Thanks for using our app! \n شكرا على استخدامك لتطبيقنا  ",
                                         font=("Arial", 15, "bold"))

        self.thanks_label.pack(pady=7)


        self.instructions_label = ctk.CTkLabel(about_frame,
                                               text="Instructions :\n1. Enter a YouTube URL.\n2. Choose the file type and quality.\n3. Click Download.\nNote: If you have an issue with the link not pasting in its place, whether you clicked the button or used the Ctrl+V shortcut, simply change the keyboard language to English.\n\nالتعليمات :\n1. أدخل رابط يوتيوب.\n2. اختر نوع الملف والجودة.\n3. انقر على تحميل.\nملاحظة: إذا واجهت مشكلة في عدم لصق الرابط في مكانه، غير لغة المفاتيح إلى انجليزية ",
                                               font=("Arial", 13), wraplength=468, justify="left")

        self.instructions_label.pack(pady=7)


        settings_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        settings_frame.pack(pady=7)

        def open_instructions():
            import webbrowser
            exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
            index_path = os.path.join(exe_dir, "index", "index.html")
            if os.path.exists(index_path):
                webbrowser.open(f"file://{index_path}")


        instructions_button = ctk.CTkButton(about_frame, text="View Instructions - عرض التعليمات",
                                            command=open_instructions, font=("Arial", 17))

        instructions_button.pack(pady=7)


        self.notification_check = ctk.CTkCheckBox(settings_frame, text="Enable Notifications",
                                                  variable=self.notifications_enabled,
                                                  command=self.save_settings,
                                                  font=("Arial", 13),
                                                  corner_radius=5)

        self.notification_check.pack(side="left", padx=15)


        self.tooltip_check = ctk.CTkCheckBox(settings_frame, text="Show Reset Tooltip",
                                             variable=self.tooltip_enabled,
                                             command=self.save_settings,
                                             font=("Arial", 13),
                                             corner_radius=5)

        self.tooltip_check.pack(side="left", padx=15)


        self.rights_label = ctk.CTkLabel(about_frame,
                                         text="\n\n All rights reserved by developer Hariz Hammouda and contributor AI Grok\n© 2025",
                                         font=("Arial", 13))

        self.rights_label.pack(pady=7)

    def setup_contribute_tab(self):
        # إنشاء إطار قابلاً للتمرير داخل التبويب
        scrollable_frame = ctk.CTkScrollableFrame(self.contribute_tab, fg_color="transparent", height=550)
        scrollable_frame.pack(fill="both", expand=True)

        self.contribute_title = ctk.CTkLabel(scrollable_frame,
                                             text="Contribute to YouTube Downloader \n ساهم في تطوير تطبيقنا",
                                             font=("Arial", 18, "bold"), justify="center")
        self.contribute_title.pack(pady=10 * 0.75, anchor="center")

        self.contribute_info = ctk.CTkLabel(scrollable_frame,
                                            text="Contribute Info : We are working to resolve issues with the application and improve it. Therefore, if you want to contribute and encounter an error in the app, immediately press the 'Send Log File' button. A copy of the error log file will automatically be sent to us for correction. A small step that improves our app, and thank you!\n\nساهم : نحن نسعى لحل مشاكل التطبيق وتطويره لذا إذا كنت تريد المساهمة و إذا ظهر لك خطأ في التطبيق اضغط على الفور على زر تحت هنا سيتم إرسال نسخة من ملف سجل الأخطاء إلينا تلقائيًا لتصحيحه\n خطوة صغيرة تحسن تطبيقنا ",
                                            font=("Arial", 15), justify="center", wraplength=550 * 0.75)
        self.contribute_info.pack(pady=10 * 0.75, anchor="center")

        self.send_log_button = ctk.CTkButton(scrollable_frame, text="Send Debug Log",
                                             command=self.send_debug_log, width=150 * 0.75, height=40 * 0.75,
                                             font=("Arial", 15))
        self.send_log_button.pack(pady=10 * 0.75)

        self.ideas_label = ctk.CTkLabel(scrollable_frame, text="👇Your Ideas👇",
                                        font=("Arial", 15), justify="center", width=50 * 0.75, height=40 * 0.75)
        self.ideas_label.pack(pady=5 * 0.75, anchor="center")

        self.ideas_entry = ctk.CTkTextbox(scrollable_frame, height=30 * 0.75, width=600 * 0.75, font=("Arial", 15),
                                          wrap="word")
        self.ideas_entry.pack(pady=5 * 0.75)

        self.send_ideas_button = ctk.CTkButton(scrollable_frame, text="Send Ideas",
                                               command=self.send_ideas, width=150 * 0.75, height=40 * 0.75,
                                               font=("Arial", 15))
        self.send_ideas_button.pack(pady=10 * 0.75)

        self.contact_label = ctk.CTkLabel(scrollable_frame, text="👇Contact Us👇",
                                          font=("Arial", 15), justify="center")
        self.contact_label.pack(pady=5 * 0.75, anchor="center")

        self.website_button = ctk.CTkButton(scrollable_frame, text="Visit Our Website",
                                            command=lambda: webbrowser.open("https://hammouda-h.devunion.dev/"),
                                            width=150 * 0.75, height=40 * 0.75, font=("Arial", 15))
        self.website_button.pack(pady=10 * 0.75)

    def check_url(self, event):
        url = self.url_entry.get().strip()
        youtube_regex = (
            r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})'
        )
        if url:
            if "&list=" in url or "?list=" in url:
                self.progress_label.pack()
                self.progress_label.configure(
                    text="Invalid URL, please use the video share link instead of a playlist link")
                self.video_title_label.configure(text="Video Title: No video selected")
                self.disable_fields()
                self.root.after(3000, lambda: self.progress_label.pack_forget())
                log_message("URL contains playlist parameters, please use the video share link")
            elif re.match(youtube_regex, url):
                self.progress_label.pack()
                self.progress_label.configure(text="Checking URL...")
                self.start_dots_animation()
                thread = threading.Thread(target=self.fetch_video_info, args=(url,), daemon=True)
                thread.start()
            else:
                self.progress_label.pack()
                self.progress_label.configure(text="Invalid URL, please enter a valid YouTube video link")
                self.video_title_label.configure(text="Video Title: No video selected")
                self.disable_fields()
                self.root.after(3000, lambda: self.progress_label.pack_forget())
                log_message("URL does not match valid YouTube pattern")
        else:
            self.progress_label.pack()
            self.progress_label.configure(text="Please enter a URL")
            self.video_title_label.configure(text="Video Title: No video selected")
            self.disable_fields()
            self.root.after(3000, lambda: self.progress_label.pack_forget())
            log_message("URL is empty")
    def fetch_video_info(self, url):
        log_message(f"Fetching video info for URL: {url}")
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                self.info_dict = ydl.extract_info(url, download=False)
                log_message("Video info fetched successfully.")
                resolutions = sorted(set(f["height"] for f in self.info_dict["formats"] if f.get("height")),
                                     reverse=True)
                self.quality_menu.configure(
                    values=["choose"] + [f"{res}p" for res in resolutions] if resolutions else ["choose", "720p"])
                self.quality_var.set("choose")
                self.root.after(0, self.enable_fields)
                self.root.after(0, lambda: self.video_title_label.configure(
                    text=f"Video Title: {self.info_dict.get('title', 'Unknown')}"
                ))
        except Exception as e:
            log_message(f"Error fetching video info: {str(e)}")
            self.root.after(0, lambda: self.progress_label.configure(
                text="The server is not connected, please check your internet connection"))
            self.root.after(0, lambda: self.video_title_label.configure(text="Video Title: No video selected"))
        finally:
            self.root.after(0, self.stop_dots_animation)
            self.root.after(0, self.hide_check_progress)

    def start_dots_animation(self, text="Checking URL", use_merge_label=False):
        self.dots_animation_running = True
        self.dots_step = 0
        self.dots_text = text
        self.dots_use_merge_label = use_merge_label
        if use_merge_label:
            self.merge_label.pack()
        else:
            self.progress_label.pack()
        self.update_dots()

    def update_dots(self):
        if not hasattr(self, 'dots_animation_running') or not self.dots_animation_running:
            return

        label = self.merge_label if self.dots_use_merge_label else self.progress_label
        if self.dots_step == 0:
            label.configure(text=f"- {self.dots_text} -")
        elif self.dots_step == 1:
            label.configure(text=f"- - {self.dots_text} - -")
        elif self.dots_step == 2:
            label.configure(text=f"- - - {self.dots_text} - - -")
        elif self.dots_step == 3:
            label.configure(text=f"- - - - {self.dots_text} - - - -")
        elif self.dots_step == 4:
            label.configure(text=f"- - - {self.dots_text} - - -")
        elif self.dots_step == 5:
            label.configure(text=f"- - {self.dots_text} - -")
        elif self.dots_step == 6:
            label.configure(text=f"- {self.dots_text} -")
            self.dots_step = -1

        self.dots_step += 1
        self.root.after(500, self.update_dots)

    def stop_dots_animation(self):
        if hasattr(self, 'dots_animation_running'):
            self.dots_animation_running = False
            self.progress_label.configure(text="")  # إعادة النص إلى الوضع الافتراضي

    def hide_check_progress(self):
        self.progress.set(0)
        self.progress.pack_forget()
        self.progress_label.pack_forget()

    def update_type(self, *args):
        value = self.type_var.get()
        if value in ["mp3     (Audio, Classic)", "OPUS   (Audio, Faster & Smaller)"]:
            self.quality_menu.configure(state="disabled")
            self.download_button.configure(state="normal")
        elif value == "mp4     (Video)":
            self.quality_menu.configure(state="normal")
            self.download_button.configure(state="disabled" if self.quality_var.get() == "choose" else "normal")
        else:  # "choose"
            self.quality_menu.configure(state="disabled")
            self.download_button.configure(state="disabled")

    def update_quality(self, *args):
        self.download_button.configure(state="normal" if self.quality_var.get() != "choose" else "disabled")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_entry.configure(state="normal")
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)
            self.output_entry.configure(state="disabled")

    def paste_from_clipboard(self):
        if self.is_paste_active:
            return
        clipboard_content = pyperclip.paste().strip()
        if len(clipboard_content) > 200:
            self.progress_label.pack()
            self.progress_label.configure(text="Link is too long!")
            return
        if "youtube.com" in clipboard_content or "youtu.be" in clipboard_content:
            self.is_paste_active = True
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clipboard_content)
            self.check_url(None)
        else:
            self.progress_label.pack()
            self.progress_label.configure(text="No YouTube link found in clipboard!")

    def enable_fields(self):
        self.url_entry.configure(state="normal")
        self.clear_url_button.configure(state="normal")
        self.paste_button.configure(state="normal")
        self.output_entry.configure(state="normal")
        self.browse_button.configure(state="normal")
        self.type_menu.configure(state="normal")
        self.quality_menu.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.reset_button.configure(state="normal")  # تفعيل زر إعادة تحميل

    def disable_fields(self):
        self.url_entry.configure(state="disabled")
        self.clear_url_button.configure(state="disabled")
        self.paste_button.configure(state="disabled")
        self.output_entry.configure(state="disabled")
        self.browse_button.configure(state="disabled")
        self.type_menu.configure(state="disabled")
        self.quality_menu.configure(state="disabled")
        self.download_button.configure(state="disabled")

    def start_download(self):
        log_message("Starting download process...")
        if self.is_downloading:
            log_message("Download already in progress!")
            self.progress_label.pack()
            self.progress_label.configure(text="A download is already in progress!")
            return

        if not self.info_dict:
            log_message("No video info available!")
            self.progress_label.pack()
            self.progress_label.configure(text="No video info available!")
            return

        self.is_downloading = True
        self.disable_non_url_fields()
        self.disable_fields()
        self.download_button.configure(state="disabled")
        self.progress.pack()
        self.progress_label.pack()
        self.progress_label.configure(text="Download audio... (1/2) 0%")  # Initialize for audio phase
        self.progress.configure(mode="determinate")
        self.progress.set(0)# Reset progress bar
        self.root.update_idletasks()  # Force UI update

        url = self.url_entry.get()
        output_path = self.output_entry.get().strip()
        if not output_path:
            messagebox.showwarning("warning", "Select the save path here!", parent=self.root)
            self.is_downloading = False
            self.reset_state()
            return
        file_type = self.type_var.get()
        quality = self.quality_var.get().replace("p",
                                                 "") if file_type == "mp4     (Video)" and self.quality_var.get() != "choose" else None

        exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        ffmpeg_path = os.path.join(exe_dir, "ffmpeg.exe")
        ffprobe_path = os.path.join(exe_dir, "ffprobe.exe")
        ytdlp_path = os.path.join(exe_dir, "yt-dlp.exe")

        if file_type == "mp3     (Audio, Classic)":
            self.download_thread = threading.Thread(target=self.download_audio,
                                                    args=(url, output_path, ytdlp_path, ffmpeg_path, ffprobe_path))
        elif file_type == "OPUS   (Audio, Faster & Smaller)":
            self.download_thread = threading.Thread(target=self.download_webm,
                                                    args=(url, output_path, ytdlp_path, ffmpeg_path, ffprobe_path))
        elif file_type == "mp4     (Video)" and quality:
            self.download_thread = threading.Thread(target=self.download_video_audio,
                                                    args=(url, output_path, quality, ytdlp_path, ffmpeg_path,
                                                          ffprobe_path))
        else:
            self.is_downloading = False
            self.progress_label.configure(text="Please select a valid file type or quality!")
            self.root.update_idletasks()
            self.reset_state()
            return

        self.download_thread.start()

    def download_audio(self, url, output_path, ytdlp_path, ffmpeg_path, ffprobe_path):
        log_message(f"Starting audio download for URL: {url}")
        sanitized_title = sanitize_filename(self.info_dict.get('title', 'audio'))
        audio_file = os.path.join(output_path, f"{sanitized_title}_audio.mp3")
        thumbnail_file = os.path.join(output_path, f"{sanitized_title}_audio.mp3.jpg")
        final_audio_file = os.path.join(output_path, f"{sanitized_title}.mp3")
        command = [
            ytdlp_path, url, "-o", audio_file, "--write-thumbnail", "--convert-thumbnails", "jpg", "--force-overwrite",
            "--ffmpeg-location", ffmpeg_path, "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", "192", "--no-write-subs", "--retries", "10",
            "--hls-prefer-native", "--concurrent-fragments", "1", "--progress",
            "--progress-template", "[download] %(progress._percent_str)s", "--console-title"
        ]
        log_message(f"Attempting to download audio and thumbnail to: {audio_file}, {thumbnail_file}")
        success = self.run_download_phase(command, "Download audio... (1/1)", audio_file, is_audio=True)
        if success:
            if os.path.exists(thumbnail_file):
                log_message("Thumbnail downloaded successfully, starting cover art embedding...")
                command_embed = [
                    ffmpeg_path, "-i", audio_file, "-i", thumbnail_file, "-c", "copy",
                    "-map", "0:a", "-map", "1:v", "-metadata:s:v", "title=Cover Art",
                    "-metadata:s:v", "comment=Cover Art", "-id3v2_version", "3",
                    "-y", final_audio_file
                ]
                embed_success = self.run_download_phase(command_embed, "Download audio... (1/1)", final_audio_file,
                                                        is_merge=True, is_audio=True)
                self.dots_animation_running = False
                self.merge_label.pack_forget()
                if embed_success:
                    log_message(f"Cover art embedded successfully into {final_audio_file}")
                    self.downloaded_file = final_audio_file
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                        log_message(f"Deleted temporary audio file: {audio_file}")
                else:
                    log_message("Failed to embed cover art, keeping original MP3")
                    self.downloaded_file = audio_file
                if os.path.exists(thumbnail_file):
                    os.remove(thumbnail_file)
                    log_message(f"Deleted temporary thumbnail file: {thumbnail_file}")
            else:
                log_message("Thumbnail not found, proceeding with original MP3")
                self.downloaded_file = audio_file
                self.dots_animation_running = False
                self.merge_label.pack_forget()
            self.progress_label.configure(text="Download successful!")
            self.root.update()
            time.sleep(2)
            self.root.after(0, lambda: self.show_success_message(output_path))
            self.root.after(0, self.show_windows_notification)
            self.hide_progress()
            self.reset_state()
        else:
            self.dots_animation_running = False
            self.merge_label.pack_forget()
            self.hide_progress()
            self.reset_state()
        self.is_downloading = False

    def download_webm(self, url, output_path, ytdlp_path, ffmpeg_path, ffprobe_path):
        log_message(f"Starting OPUS audio download for URL: {url}")
        sanitized_title = sanitize_filename(self.info_dict.get('title', 'audio'))
        final_audio_file = os.path.join(output_path, rf"{sanitized_title}.opus")  # الملف النهائي بنهاية .opus

        # ضبط ترميز النظام على UTF-8
        os.system("chcp 65001 > nul")

        # أمر yt-dlp لتحميل الصوت مباشرة كـ .opus
        command = [
            ytdlp_path, url, "-o", final_audio_file, "--force-overwrite",
            "--ffmpeg-location", ffmpeg_path, "--extract-audio",
            "--audio-format", "opus", "--audio-quality", "192", "--no-write-subs",
            "--retries", "10", "--hls-prefer-native", "--concurrent-fragments", "1",
            "--progress", "--progress-template", "[download] %(progress._percent_str)s",
            "--console-title", "--no-clean-infojson", "--output-na-placeholder", " "
        ]

        log_message(f"Attempting to download audio to: {final_audio_file}")
        success = self.run_download_phase(command, "Download OPUS audio... (1/1)", final_audio_file)

        if success and os.path.exists(final_audio_file):
            log_message("OPUS audio downloaded successfully.")
            self.downloaded_file = final_audio_file
            self.progress_label.configure(text="Download successful!")
            self.root.update()
            time.sleep(2)
            self.root.after(0, lambda: self.show_success_message(output_path))
            self.root.after(0, self.show_windows_notification)
            self.hide_progress()
            self.reset_state()
        else:
            log_message("Download failed or audio file not created.")
            self.progress_label.configure(text="Download failed!")
            self.hide_progress()
            self.reset_state()
        self.is_downloading = False

    def download_video_audio(self, url, output_path, quality, ytdlp_path, ffmpeg_path, ffprobe_path):
        log_message(f"Starting video and audio download for URL: {url} at {quality}p")
        sanitized_title = sanitize_filename(self.info_dict.get('title', 'video'))
        video_file = os.path.join(output_path, f"{sanitized_title}_video.mp4")
        audio_file = os.path.join(output_path, f"{sanitized_title}_audio.mp4")
        final_file = os.path.join(output_path, f"{sanitized_title}_final.mp4")

        # Phase 1: Download audio
        self.progress["value"] = 0
        self.progress_label.configure(text="Download audio... (1/2) 0%")
        self.root.update_idletasks()
        command_audio = [
            ytdlp_path, url, "-o", audio_file, "--force-overwrite",
            "--ffmpeg-location", ffmpeg_path, "-f", "bestaudio", "--no-write-subs",
            "--retries", "10", "--hls-prefer-native", "--concurrent-fragments", "1", "--progress",
            "--progress-template", "[download] %(progress._percent_str)s", "--console-title"
        ]
        log_message(f"Attempting to download audio to: {audio_file}")
        if not self.run_download_phase(command_audio, "Download audio... (1/2)", audio_file, is_audio=False):
            self.hide_progress()
            self.reset_state()
            self.is_downloading = False
            return

        # Phase 2: Download video
        self.progress.set(0)
        self.progress_label.configure(text="Download video... (2/2) 0%")
        self.root.update()
        self.root.update_idletasks()
        log_message("Reset progress for video download phase")
        command_video = [
            ytdlp_path, url, "-o", video_file, "--force-overwrite",
            "--ffmpeg-location", ffmpeg_path, "-f", f"bestvideo[height<={quality}]",
            "--no-write-subs", "--retries", "10", "--hls-prefer-native", "--concurrent-fragments", "1", "--progress",
            "--progress-template", "[download] %(progress._percent_str)s", "--console-title"
        ]
        log_message(f"Attempting to download video to: {video_file}")
        if not self.run_download_phase(command_video, "Download video... (2/2)", video_file, is_audio=False):
            self.hide_progress()
            self.reset_state()
            self.is_downloading = False
            return

        # Phase 3: Merge video and audio
        self.progress.configure(mode="indeterminate")
        self.progress["value"] = 0
        self.progress_label.configure(text="Merging video and audio...")
        self.merge_label.pack()
        self.merge_label.configure(text="Merging")
        self.root.update_idletasks()
        log_message(f"Attempting to merge video and audio into: {final_file}")
        command_merge = [
            ffmpeg_path, "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "copy",
            "-map", "0:v:0", "-map", "1:a:0", "-y", final_file
        ]
        if not self.run_download_phase(command_merge, "Merging video and audio...", final_file, is_merge=True,
                                       is_audio=False):
            self.merge_label.pack_forget()
            self.hide_progress()
            self.reset_state()
            self.is_downloading = False
            return

        # Cleanup
        if os.path.exists(final_file):
            try:
                if os.path.exists(video_file):
                    os.remove(video_file)
                    log_message(f"Deleted temporary video file: {video_file}")
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    log_message(f"Deleted temporary audio file: {audio_file}")
            except Exception as e:
                log_message(f"Error deleting temporary files: {str(e)}")
            self.downloaded_file = final_file
            self.merge_label.pack_forget()
            self.progress.configure(mode="determinate")
            self.progress["value"] = 100
            self.progress_label.configure(text="Download successful!")
            self.root.update_idletasks()
            time.sleep(2)
            self.root.after(0, lambda: self.show_success_message(output_path))
            self.root.after(0, self.show_windows_notification)
            self.hide_progress()
            self.reset_state()

        self.is_downloading = False

    def run_download_phase(self, command, phase_text, output_file, is_merge=False, is_audio=False, max_retries=3):
        log_message(f"Executing command: {' '.join(command)}")
        retries = 0
        success = False

        if is_merge:
            self.progress.configure(mode="indeterminate")
            self.progress_label.configure(text=phase_text)
            self.root.update()
        else:
            self.progress_label.configure(text=phase_text)
            self.progress.pack()
            self.root.update()

        while retries < max_retries:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       universal_newlines=True, encoding='utf-8', errors='ignore',
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            self.download_process = process
            last_progress = 0
            is_converting = False

            while True:
                line = process.stdout.readline().strip()
                if line:
                    log_message(f"output: {line}")
                    if "[download]" in line and not is_merge:
                        try:
                            match = re.search(r"(\d+\.\d+|\d+)%", line)
                            if match:
                                percentage = float(match.group(0).rstrip("%"))
                                if percentage >= last_progress:
                                    last_progress = percentage
                                    self.update_progress(f"{percentage}%", phase_text)
                                    log_message(f"Download progress: {percentage}%")
                                    if is_audio and percentage >= 100.0 and not is_converting:
                                        self.progress_label.configure(text=phase_text.split(" (")[0])
                                        self.start_dots_animation("Processing", use_merge_label=True)
                                        is_converting = True
                        except (ValueError, IndexError):
                            log_message(f"Failed to parse progress from: {line}")
                    elif is_audio and "[ExtractAudio]" in line and not is_merge:
                        if not is_converting:
                            self.progress_label.configure(text=phase_text.split(" (")[0])
                            self.start_dots_animation("Processing", use_merge_label=True)
                            is_converting = True
                    if "error" in line.lower() or "failed" in line.lower() or "[WinError 32]" in line:
                        if retries < max_retries - 1:
                            log_message(f"Retry {retries + 1}/{max_retries} due to error: {line}")
                            time.sleep(2)
                            process.terminate()
                            break
                        else:
                            self.dots_animation_running = False
                            self.merge_label.pack_forget()
                            self.progress_label.configure(text="Error: Download failed")
                            self.root.update()
                            time.sleep(3)
                            self.hide_progress()
                            self.reset_state()
                            self.is_downloading = False
                            return False

                if process.poll() is not None:
                    break
                time.sleep(0.1)

            stdout, stderr = process.communicate()
            if stdout:
                log_message(f"Remaining output: {stdout}")
            if stderr:
                log_message(f"Remaining stderr: {stderr}")
                if "error" in stderr.lower() or "failed" in stderr.lower():
                    if is_merge and "error" in stderr.lower():
                        log_message(f"Merge error: {stderr}")
                        self.dots_animation_running = False
                        self.merge_label.pack_forget()
                        return False
                    if retries < max_retries - 1:
                        retries += 1
                        continue
                    self.dots_animation_running = False
                    self.merge_label.pack_forget()
                    self.progress_label.configure(text="Error: Download failed")
                    self.root.update()
                    time.sleep(3)
                    self.hide_progress()
                    self.reset_state()
                    self.is_downloading = False
                    return False

            if not os.path.exists(output_file):
                log_message(f"Output file not created: {output_file}")
                if retries < max_retries - 1:
                    retries += 1
                    continue
                self.dots_animation_running = False
                self.merge_label.pack_forget()
                self.progress_label.configure(text="Error: Download failed")
                self.root.update()
                time.sleep(3)
                self.hide_progress()
                self.reset_state()
                self.is_downloading = False
                return False

            success = True
            break

        if success:
            log_message(f"Phase {phase_text} completed successfully")
        else:
            self.dots_animation_running = False
            self.merge_label.pack_forget()
            self.progress_label.configure(text="Error: Download failed")
            self.root.update()
            time.sleep(3)

        return success

    def update_progress(self, p, phase_text):
        try:
            value = float(p.rstrip('%'))  # Convert percentage to float (e.g., 50.0% -> 50.0)
            if 0 <= value <= 100:  # Ensure value is within valid range
                self.progress.set(value / 100)  # Restore original behavior for progress bar
                self.progress_label.configure(text=f"{phase_text} {value:.1f}%")
                self.root.update()  # Force full UI update
                log_message(f"Updated progress: {value}% for {phase_text}")
            else:
                log_message(f"Invalid progress value: {value}")
                self.progress_label.configure(text=f"{phase_text} 0%")
                self.root.update()
        except (ValueError, TypeError):
            log_message(f"Failed to parse progress value: {p}")
            self.progress_label.configure(text=f"{phase_text} 0%")
            self.root.update()

    def hide_progress(self):
        self.progress.pack_forget()
        self.progress_label.pack_forget()
        self.merge_label.pack_forget()
        self.progress.set(0)


    def reset_state(self):
        self.is_downloading = False
        self.download_button.configure(state="normal")
        self.progress.set(0)
        self.is_paste_active = False
        self.download_process = None
        self.enable_fields()
        log_message("Application state reset.")

        if self.download_process and self.download_process.poll() is None:
            self.download_process.terminate()
            try:
                self.download_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.download_process.kill()

    def on_closing(self):
        if self.is_downloading:
            response = messagebox.askyesno(
                "Warning",
                "Download is in progress. Do you want to close the application?",
                icon="warning",
                parent=self.root
            )
            if response:  # إذا اختير "Yes"
                if hasattr(self, 'download_thread') and self.download_thread and self.download_thread.is_alive():
                    self.download_thread.join(timeout=1)
                if hasattr(self, 'download_process') and self.download_process and self.download_process.poll() is None:
                    self.download_process.terminate()
                    try:
                        self.download_process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self.download_process.kill()
                self.reset_state()
                self.root.destroy()
            # إذا اختير "No"، لا نفعل شيئًا والنافذة تختفي تلقائيًا
        else:  # إذا لم يكن هناك تحميل
            if hasattr(self, 'download_thread') and self.download_thread and self.download_thread.is_alive():
                self.download_thread.join(timeout=1)
            if hasattr(self, 'download_process') and self.download_process and self.download_process.poll() is None:
                self.download_process.terminate()
                try:
                    self.download_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.download_process.kill()
            self.reset_state()
            self.root.destroy()



    def send_debug_log(self):
        if not os.path.exists(log_file_path):
            self.send_log_button.configure(text="File not found!")
            self.root.after(5000, lambda: self.send_log_button.configure(text="Send Debug Log"))
            return

        self.send_log_button.configure(text="Sending...")
        self.root.update()

        bot_token = ""#Confidential information could not be shown, so it was deleted. Telegram bot token and ID.
        chat_id = ""#Confidential information could not be shown, so it was deleted. Telegram bot token and ID.

        if not bot_token or not chat_id:
            self.send_log_button.configure(text="error: BOT_TOKEN or CHAT_ID Not found!")
            self.root.after(5000, lambda: self.send_log_button.configure(text="Send Debug Log"))
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        try:
            with open(log_file_path, "rb") as file:
                files = {"document": (os.path.basename(log_file_path), file)}
                data = {"chat_id": chat_id, "caption": "Debug log file from YouTube Downloader"}
                response = requests.post(url, data=data, files=files)
                response.raise_for_status()
                self.send_log_button.configure(text="Sent successfully!")
        except Exception as e:
            log_message(f"Error sending debug log to Telegram: {str(e)}")
            self.send_log_button.configure(text=f"Error: {str(e)}")
        self.root.after(5000, lambda: self.send_log_button.configure(text="Send Debug Log"))

    def send_ideas(self):
        ideas = self.ideas_entry.get("1.0", "end").strip()
        if not ideas:
            self.send_ideas_button.configure(text="No ideas to send!")
            self.root.after(5000, lambda: self.send_ideas_button.configure(text="Send Ideas"))
            return

        self.send_ideas_button.configure(text="Sending...")
        self.root.update()

        bot_token = ""#Confidential information could not be shown, so it was deleted. Telegram bot token and ID.
        chat_id = ""#Confidential information could not be shown, so it was deleted. Telegram bot token and ID.

        if not bot_token or not chat_id:
            self.send_ideas_button.configure(text="Error: BOT_TOKEN or CHAT_ID Not found!")
            self.root.after(5000, lambda: self.send_ideas_button.configure(text="Send Ideas"))
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            data = {"chat_id": chat_id, "text": f"Ideas from YouTube Downloader user:\n{ideas}"}
            response = requests.post(url, data=data)
            response.raise_for_status()
            self.send_ideas_button.configure(text="Sent successfully!")
            self.ideas_entry.delete("1.0", "end")
        except Exception as e:
            log_message(f"Error sending ideas to Telegram: {str(e)}")
            self.send_ideas_button.configure(text=f"Error: {str(e)}")
        self.root.after(5000, lambda: self.send_ideas_button.configure(text="Send Ideas"))

    def disable_non_url_fields(self):
        self.output_entry.configure(state="disabled")
        self.browse_button.configure(state="disabled")
        self.type_menu.configure(state="disabled")
        self.quality_menu.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.reset_button.configure(state="disabled")

    def reset_app(self):
        self.url_entry.delete(0, "end")
        self.video_title_label.configure(text="Video Title: No video selected")
        self.info_dict = None
        self.type_var.set("choose")
        self.quality_var.set("choose")
        self.quality_menu.configure(values=["choose"])
        self.output_entry.configure(state="normal")
        self.output_entry.delete(0, "end")
        self.output_entry.configure(state="disabled")
        self.progress.set(0)
        self.progress.pack_forget()
        self.progress_label.pack_forget()
        self.merge_label.pack_forget()
        self.is_downloading = False
        self.download_process = None
        self.is_paste_active = False
        self.url_entry.configure(state="normal")
        self.clear_url_button.configure(state="normal")
        self.paste_button.configure(state="normal")
        self.disable_non_url_fields()
        log_message("Application reset to initial state.")

    def create_tooltip(self, widget, text):
        if not self.tooltip_enabled.get():
            return
        tooltip = None
        after_id = None

        def show_tooltip(event):
            nonlocal tooltip, after_id
            if after_id:
                widget.after_cancel(after_id)  # إلغاء أي تأخير سابق
            after_id = widget.after(1000, lambda: _show_tooltip(widget, text))  # تأخير 2 ثانية

        def _show_tooltip(widget, text):
            nonlocal tooltip
            x = widget.winfo_rootx() - 110
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            tooltip.attributes('-topmost', True)
            label = tk.Label(tooltip, text=text, font=("Arial", 15),
                             background="#4d4d4d", foreground="#ffffff",
                             borderwidth=0, padx=10, pady=5)
            label.pack()
            tooltip.configure(bg="#4d4d4d")
            # إخفاء التعليق بعد 5 ثواني
            widget.after(5000, lambda: hide_tooltip(None) if tooltip else None)

        def hide_tooltip(event):
            nonlocal tooltip, after_id
            if after_id:
                widget.after_cancel(after_id)  # إلغاء التأخير إذا تحرك المؤشر
            if tooltip and hasattr(tooltip, 'destroy'):
                tooltip.destroy()
                tooltip = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def show_success_message(self, output_path):
        response = messagebox.askyesno(
            "Download Complete",
            "Download complete! Open folder?",
            parent=self.root
        )
        if response:
            os.startfile(output_path)

    def show_windows_notification(self):
        if not self.notifications_enabled.get():
            return
        exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        icon_path = os.path.join(exe_dir, "img", "download.ico")
        if os.path.exists(icon_path):
            win11toast.toast(
                title="Download Complete!",
                body=f"Downloaded:\n{os.path.basename(self.downloaded_file)}",
                duration="short",
                app_id="YouTube Downloader",
                icon=icon_path  # إضافة الأيقونة الصغيرة
            )
        else:
            win11toast.toast(
                title="Download Complete!",
                body=f"Downloaded:\n{os.path.basename(self.downloaded_file)}",
                duration="short",
                app_id="YouTube Downloader"
            )  # بدون أيقونة إذا لم يوجد الملف

if __name__ == "__main__":
    root = ctk.CTk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()