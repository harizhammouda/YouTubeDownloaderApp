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
from yt_dlp import YoutubeDL
from PIL import Image
from tkinter import messagebox
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
    """Remove invalid characters and extra spaces from the filename."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader 3.0")
        # حساب الموقع لتوسيط النافذة
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 900) // 2
        y = (screen_height - 750) // 2 - 50
        self.root.geometry(f"900x750+{x}+{y}")
        self.root.resizable(False, False)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        icon_path = os.path.join(exe_dir, "img", "download.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.is_downloading = False
        self.downloaded_file = None
        self.download_process = None
        self.info_dict = None
        self.is_paste_active = False

        self.settings_file = os.path.join(os.path.dirname(log_file_path), "settings.txt")
        self.notifications_enabled = tk.BooleanVar(value=True)
        self.tooltip_enabled = tk.BooleanVar(value=True)
        self.load_settings()

        # التحقق من الفتح الأول
        if not self.is_first_run_checked():
            import webbrowser
            index_path = os.path.join(exe_dir, "index", "index.html")
            if os.path.exists(index_path):
                webbrowser.open(f"file://{index_path}")
            self.mark_first_run()

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def is_first_run_checked(self):
        # التحقق مما إذا كان التطبيق قد فُتح من قبل
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                settings = dict(line.strip().split("=", 1) for line in f if "=" in line)
                return settings.get("first_run", "False") == "True"
        except FileNotFoundError:
            return False

    def mark_first_run(self):
        # وضع علامة أن التطبيق فُتح لأول مرة
        with open(self.settings_file, "a", encoding="utf-8") as f:
            f.write("first_run=True\n")

    def create_widgets(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.welcome_label = ctk.CTkLabel(title_frame, text="Welcome to YouTube Downloader",
                                          font=("Arial", 20, "bold"))
        self.welcome_label.pack(pady=5)
        self.version_label = ctk.CTkLabel(title_frame, text="Version 3.0",
                                          text_color="gray", font=("Arial", 15))
        self.version_label.pack()
        title_frame.pack(fill="x")

        self.notebook = ctk.CTkTabview(self.main_frame)
        self.download_tab = self.notebook.add("Download")
        self.about_tab = self.notebook.add("About")
        self.contribute_tab = self.notebook.add("Contribute")
        self.update_tab = self.notebook.add("Update")  # إضافة تبويب Update
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
        self.url_label.pack(anchor="w", pady=2)

        refresh_image = ctk.CTkImage(light_image=Image.open("img/img2.png"), size=(16, 16))
        self.reset_button = ctk.CTkButton(self.download_tab, image=refresh_image, text="", width=24, height=24,
                                          fg_color="#333333", corner_radius=12,
                                          command=self.reset_app)
        self.reset_button.place(x=800, y=0)
        self.create_tooltip(self.reset_button,
                            "Click to reset the app for a \n new video link or to fix errors.")

        self.url_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.url_entry = ctk.CTkEntry(self.url_frame, width=460, height=40, font=("Arial", 15),
                                      placeholder_text="Put video link here .URL", placeholder_text_color="gray")
        self.url_entry.pack(side="left", padx=(25, 5))

        self.clear_url_button = ctk.CTkButton(self.url_frame, text="X", width=24, height=24, font=("Arial", 12),
                                              fg_color="#333333", hover_color="#4d4d4d", corner_radius=12,
                                              command=lambda: self.url_entry.delete(0, "end"))
        self.clear_url_button.place(relx=1.0, x=-45, y=8)
        self.url_frame.pack(pady=5, padx=(5, 20))

        self.paste_button = ctk.CTkButton(self.download_tab, text="Paste",
                                          command=self.paste_from_clipboard, width=120, height=40, font=("Arial", 15))
        self.paste_button.pack(pady=5)

        self.separator = ctk.CTkFrame(self.download_tab, height=2, width=700, fg_color="gray50", corner_radius=5)
        self.separator.pack(anchor="center", pady=10)

        self.video_title_label = ctk.CTkLabel(self.download_tab, text="Video Title: No video selected",
                                              font=("Arial", 15), wraplength=460, justify="center")
        self.video_title_label.pack(anchor="center", pady=2)



        self.progress = ctk.CTkProgressBar(self.download_tab, width=400)
        self.progress.set(0)
        self.progress.pack(pady=10)
        self.progress.pack_forget()
        self.progress_label = ctk.CTkLabel(self.download_tab, text="", font=("Arial", 15))
        self.progress_label.pack(pady=2)
        self.progress_label.pack_forget()
        self.merge_label = ctk.CTkLabel(self.download_tab, text="", font=("Arial", 15))
        self.merge_label.pack(pady=2)
        self.merge_label.pack_forget()

        self.file_path_label = ctk.CTkLabel(self.download_tab, text="Save to:", font=("Arial", 15))
        self.file_path_label.pack(anchor="w", pady=2)
        self.output_frame = ctk.CTkFrame(self.download_tab, fg_color="transparent")
        self.output_entry = ctk.CTkEntry(self.output_frame, width=350, height=40, font=("Arial", 15),
                                         placeholder_text="Select the save path here.", placeholder_text_color="gray")
        self.output_entry.pack(side="left", padx=5)
        self.output_entry.configure(state="disabled")
        self.browse_button = ctk.CTkButton(self.output_frame, text="Browse",
                                           command=self.browse_folder, width=120, height=40, font=("Arial", 15),
                                           state="disabled")
        self.browse_button.pack(side="left")
        self.output_frame.pack(pady=5, anchor="center")

        self.file_type_label = ctk.CTkLabel(self.download_tab, text="File Type:", font=("Arial", 15))
        self.file_type_label.pack(anchor="w", pady=2)
        self.type_var = ctk.StringVar(value="choose")
        self.type_var.trace("w", self.update_type)
        self.type_menu = ctk.CTkOptionMenu(self.download_tab, values=["choose", "mp4", "mp3"], variable=self.type_var,
                                           width=200, height=40, font=("Arial", 15))
        self.type_menu.configure(state="disabled")
        self.type_menu.pack(pady=5)

        self.quality_label = ctk.CTkLabel(self.download_tab, text="Quality:", font=("Arial", 15))
        self.quality_label.pack(anchor="w", pady=2)
        self.quality_var = ctk.StringVar(value="choose")
        self.quality_var.trace("w", self.update_quality)
        self.quality_menu = ctk.CTkOptionMenu(self.download_tab, values=["choose"], variable=self.quality_var,
                                              width=200, height=40, font=("Arial", 15))
        self.quality_menu.configure(state="disabled")
        self.quality_menu.pack(pady=5)

        self.download_button = ctk.CTkButton(self.download_tab, text="Download",
                                             command=self.start_download, width=150, height=40, font=("Arial", 18),
                                             state="disabled")
        self.download_button.pack(pady=20)

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
        about_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.thanks_label = ctk.CTkLabel(about_frame, text="Thanks for using our app! \n شكرا على استخدامك لتطبيقنا  ",
                                         font=("Arial", 18, "bold"))
        self.thanks_label.pack(pady=10)
        self.instructions_label = ctk.CTkLabel(about_frame, text="Instructions :\n1. Enter a YouTube URL.\n2. Choose the file type and quality.\n3. Click Download.\nNote: If you have an issue with the link not pasting in its place, whether you clicked the button or used the Ctrl+V shortcut, simply change the keyboard language to English.\n\nالتعليمات :\n1. أدخل رابط يوتيوب.\n2. اختر نوع الملف والجودة.\n3. انقر على تحميل.\nملاحظة: إذا واجهت مشكلة في عدم لصق الرابط في مكانه، غير لغة المفاتيح إلى انجليزية ",
                                               font=("Arial", 15), wraplength=550, justify="left")
        self.instructions_label.pack(pady=10)

        settings_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
        settings_frame.pack(pady=10)

        def open_instructions():
            import webbrowser
            exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
            index_path = os.path.join(exe_dir, "index", "index.html")
            if os.path.exists(index_path):
                webbrowser.open(f"file://{index_path}")

        instructions_button = ctk.CTkButton(about_frame, text="View Instructions - عرض التعليمات",
                                            command=open_instructions , font=("Arial", 20))
        instructions_button.pack(pady=10)

        self.notification_check = ctk.CTkCheckBox(settings_frame, text="Enable Notifications",
                                                  variable=self.notifications_enabled,
                                                  command=self.save_settings,
                                                  font=("Arial", 15),
                                                  corner_radius=6)
        self.notification_check.pack(side="left", padx=20)

        self.tooltip_check = ctk.CTkCheckBox(settings_frame, text="Show Reset Tooltip",
                                             variable=self.tooltip_enabled,
                                             command=self.save_settings,
                                             font=("Arial", 15),
                                             corner_radius=6)
        self.tooltip_check.pack(side="left", padx=20)
        self.rights_label = ctk.CTkLabel(about_frame, text="\n\n\n\n\n All rights reserved by developer Hariz Hammouda and contributor AI Grok\n© 2025",
                                         font=("Arial", 15))
        self.rights_label.pack(pady=10)

    def setup_contribute_tab(self):
        contribute_frame = ctk.CTkFrame(self.contribute_tab, fg_color="transparent")
        contribute_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.contribute_title = ctk.CTkLabel(contribute_frame, text="Contribute to YouTube Downloader \n ساهم في تطوير تطبيقنا",
                                             font=("Arial", 18, "bold"), justify="center")
        self.contribute_title.pack(pady=10, anchor="center")
        self.contribute_info = ctk.CTkLabel(contribute_frame, text="Contribute Info : We are working to resolve issues with the application and improve it. Therefore, if you want to contribute and encounter an error in the app, immediately press the 'Send Log File' button. A copy of the error log file will automatically be sent to us for correction. A small step that improves our app, and thank you!\n\nساهم : نحن نسعى لحل مشاكل التطبيق وتطويره لذا إذا كنت تريد المساهمة و إذا ظهر لك خطأ في التطبيق اضغط على الفور على زر تحت هنا سيتم إرسال نسخة من ملف سجل الأخطاء إلينا تلقائيًا لتصحيحه\n خطوة صغيرة تحسن تطبيقنا ",
                                            font=("Arial", 15), justify="center", wraplength=550)
        self.contribute_info.pack(pady=10, anchor="center")
        self.send_log_button = ctk.CTkButton(contribute_frame, text="Send Debug Log",
                                             command=self.send_debug_log, width=150, height=40, font=("Arial", 15))
        self.send_log_button.pack(pady=10)
        self.ideas_label = ctk.CTkLabel(contribute_frame, text="👇Your Ideas👇",
                                        font=("Arial", 15), justify="center", width=50, height=40)
        self.ideas_label.pack(pady=5, anchor="center")
        self.ideas_entry = ctk.CTkTextbox(contribute_frame, height=30, width=600, font=("Arial", 15), wrap="word")
        self.ideas_entry.pack(pady=5)
        self.send_ideas_button = ctk.CTkButton(contribute_frame, text="Send Ideas",
                                               command=self.send_ideas, width=150, height=40, font=("Arial", 15))
        self.send_ideas_button.pack(pady=10)
        self.contact_label = ctk.CTkLabel(contribute_frame, text="👇Contact Us👇",
                                          font=("Arial", 15), justify="center")
        self.contact_label.pack(pady=5, anchor="center")
        self.website_button = ctk.CTkButton(contribute_frame, text="Visit Our Website",
                                            command=lambda: webbrowser.open("https://hammouda-h.devunion.dev/"),
                                            width=150, height=40, font=("Arial", 15))
        self.website_button.pack(pady=10)

    def check_url(self, event):
        url = self.url_entry.get().strip()
        youtube_regex = (
            r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
        )
        if url:
            if re.match(youtube_regex, url):
                self.progress_label.pack()
                self.progress_label.configure(text="Checking URL...")
                self.start_dots_animation()
                thread = threading.Thread(target=self.fetch_video_info, args=(url,))
                thread.start()
            else:
                self.progress_label.pack()
                self.progress_label.configure(text="Invalid URL, please enter a valid YouTube video link")
                self.video_title_label.configure(text="Video Title: No video selected")
                self.disable_fields()
                self.root.after(3000, lambda: self.progress_label.pack_forget())
        else:
            self.progress_label.pack()
            self.progress_label.configure(text="Please enter a URL")
            self.video_title_label.configure(text="Video Title: No video selected")
            self.disable_fields()
            self.root.after(3000, lambda: self.progress_label.pack_forget())

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

    def start_dots_animation(self):
        self.dots_animation_running = True
        self.dots_step = 0
        self.update_dots()

    def update_dots(self):
        if not hasattr(self, 'dots_animation_running') or not self.dots_animation_running:
            return

        if self.dots_step == 0:
            self.progress_label.configure(text=". Checking URL .")
        elif self.dots_step == 1:
            self.progress_label.configure(text=". . Checking URL . .")
        elif self.dots_step == 2:
            self.progress_label.configure(text=". . . Checking URL . . .")
        elif self.dots_step == 3:
            self.progress_label.configure(text=". . . . Checking URL . . . .")
        elif self.dots_step == 4:
            self.progress_label.configure(text=". . . Checking URL . . .")
        elif self.dots_step == 5:
            self.progress_label.configure(text=". . Checking URL . .")
        elif self.dots_step == 6:
            self.progress_label.configure(text=". Checking URL .")
            self.dots_step = -1  # إعادة الدورة

        self.dots_step += 1
        self.root.after(500, self.update_dots)  # تحديث كل 500 مللي ثانية

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
        if value == "mp3":
            self.quality_menu.configure(state="disabled")
            self.download_button.configure(state="normal")
        elif value == "mp4":
            self.quality_menu.configure(state="normal")  # تفعيل الخانة
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
        log_message(f"is_downloading: {self.is_downloading}")

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
        self.disable_non_url_fields()  # تعطيل زر إعادة تحميل مع بدء التحميل
        self.disable_fields()
        self.download_button.configure(state="disabled")
        self.progress.pack()
        self.progress_label.pack()
        self.progress_label.configure(text="Starting download...")
        self.progress.configure(mode="determinate")
        self.progress.set(0)

        url = self.url_entry.get()
        output_path = self.output_entry.get().strip()  # .strip() لإزالة المسافات
        if not output_path:  # إذا كان الحقل فارغًا
            messagebox.showwarning("warning", "Select the save path here!", parent=self.root)
            self.is_downloading = False
            self.reset_state()
            return
        file_type = self.type_var.get()
        quality = self.quality_var.get().replace("p", "") if file_type == "mp4" and self.quality_var.get() != "choose" else None

        exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        ffmpeg_path = os.path.join(exe_dir, "ffmpeg.exe")
        ffprobe_path = os.path.join(exe_dir, "ffprobe.exe")
        log_message(f"FFmpeg path: {ffmpeg_path}")
        log_message(f"FFprobe path: {ffprobe_path}")
        if not os.path.exists(ffmpeg_path) or not os.path.exists(ffprobe_path):
            self.progress_label.configure(text="Error: FFmpeg or FFprobe not found!")
            self.root.update()
            self.is_downloading = False
            self.reset_state()
            return

        ytdlp_path = os.path.join(exe_dir, "yt-dlp.exe")
        log_message(f"yt-dlp path: {ytdlp_path}")

        if file_type == "mp3":
            self.download_thread = threading.Thread(target=self.download_audio, args=(url, output_path, ytdlp_path, ffmpeg_path, ffprobe_path))
        elif file_type == "mp4" and quality:
            self.download_thread = threading.Thread(target=self.download_video_audio, args=(url, output_path, quality, ytdlp_path, ffmpeg_path, ffprobe_path))
        else:
            self.is_downloading = False
            self.progress_label.configure(text="Please select a valid file type or quality!")
            self.root.update()
            self.reset_state()
            return

        self.download_thread.start()

    def download_audio(self, url, output_path, ytdlp_path, ffmpeg_path, ffprobe_path):
        log_message(f"Starting audio download for URL: {url}")
        sanitized_title = sanitize_filename(self.info_dict.get('title', 'audio'))
        audio_file = os.path.join(output_path, f"{sanitized_title}_audio.mp3")
        command = [
            ytdlp_path, url, "-o", audio_file, "--force-overwrite",
            "--ffmpeg-location", ffmpeg_path, "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", "192", "--no-write-subs", "--retries", "10",
            "--hls-prefer-native", "--concurrent-fragments", "1", "--progress",
            "--progress-template", "[download] %(progress._percent_str)s", "--console-title"
        ]
        success = self.run_download_phase(command, "Download audio... (1/1)", audio_file)
        if success:
            self.downloaded_file = audio_file
            self.progress_label.configure(text="Download successful!")
            self.root.update()
            time.sleep(2)
            self.root.after(0, lambda: self.show_success_message(output_path))
            self.root.after(0, self.show_windows_notification)
            self.hide_progress()
            self.reset_state()
        else:
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
        command_audio = [
            ytdlp_path, url, "-o", audio_file, "--force-overwrite",
            "--ffmpeg-location", ffmpeg_path, "-f", "bestaudio", "--no-write-subs",
            "--retries", "10", "--hls-prefer-native", "--concurrent-fragments", "1", "--progress",
            "--progress-template", "[download] %(progress._percent_str)s", "--console-title"
        ]
        if not self.run_download_phase(command_audio, "Download audio... (1/2)", audio_file):
            self.hide_progress()
            self.reset_state()
            self.is_downloading = False
            return

        # Phase 2: Download video
        command_video = [
            ytdlp_path, url, "-o", video_file, "--force-overwrite",
            "--ffmpeg-location", ffmpeg_path, "-f", f"bestvideo[height<={quality}]",
            "--no-write-subs", "--retries", "10", "--hls-prefer-native", "--concurrent-fragments", "1", "--progress",
            "--progress-template", "[download] %(progress._percent_str)s", "--console-title"
        ]
        if not self.run_download_phase(command_video, "Download video... (2/2)", video_file):
            self.hide_progress()
            self.reset_state()
            self.is_downloading = False
            return

        # Phase 3: Merge video and audio
        command_merge = [
            ffmpeg_path, "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "copy",
            "-map", "0:v:0", "-map", "1:a:0", "-y", final_file
        ]
        self.progress.configure(mode="indeterminate")
        self.progress.set(0.5)
        self.progress_label.configure(text="Merging (2/2)")
        self.merge_label.pack()
        self.merge_label.configure(text="Merging")
        self.root.update()
        if not self.run_download_phase(command_merge, "Merging (2/2)", final_file, is_merge=True):
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
            self.progress.set(1.0)
            self.progress_label.configure(text="Download successful!")
            self.root.update()
            time.sleep(2)
            self.root.after(0, lambda: self.show_success_message(output_path))
            self.root.after(0, self.show_windows_notification)
            self.hide_progress()
            self.reset_state()

        self.is_downloading = False

    def run_download_phase(self, command, phase_text, output_file, is_merge=False, max_retries=3):
        log_message(f"Executing command: {' '.join(command)}")
        retries = 0
        success = False

        while retries < max_retries:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       universal_newlines=True, encoding='utf-8', errors='ignore',
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            self.download_process = process
            last_progress = 0

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
                        except (ValueError, IndexError):
                            log_message(f"Failed to parse progress from: {line}")

                        if "error" in line.lower() or "failed" in line.lower() or "[WinError 32]" in line:
                            if retries < max_retries - 1:
                                log_message(f"Retry {retries + 1}/{max_retries} due to error: {line}")
                                time.sleep(2)
                                process.terminate()
                                break
                            else:
                                self.progress_label.configure(
                                    text="The server is not connected, please check your internet connection")
                                self.root.update()
                                time.sleep(3)
                                self.hide_progress()
                                self.reset_state()
                                self.is_downloading = False
                                return False

                if process.poll() is not None:
                    break
                time.sleep(0.1)
                if not self.root.winfo_exists():  # تحقق إذا كانت النافذة لا تزال موجودة
                    process.terminate()
                    break

            stdout, stderr = process.communicate()
            if stdout:
                log_message(f"Remaining output: {stdout}")
            if stderr:
                log_message(f"Remaining stderr: {stderr}")
                if "error" in stderr.lower() or "failed" in stderr.lower():
                    if retries < max_retries - 1:
                        retries += 1
                        continue
                    self.progress_label.configure(
                        text="The server is not connected, please check your internet connection")
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
                self.progress_label.configure(text="The server is not connected, please check your internet connection")
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
            self.progress_label.configure(text="The server is not connected, please check your internet connection")
            self.root.update()
            time.sleep(3)

        return success

    def update_progress(self, p, phase_text):
        try:
            value = float(p.rstrip('%')) or 0
            self.progress.configure(mode="determinate")
            self.progress.set(value / 100)
            self.progress_label.configure(text=f"{phase_text} ({value}%)")
            self.root.update()
            log_message(f"Updated progress: {value}% for {phase_text}")
        except ValueError:
            log_message(f"Failed to update progress with value: {p}")
            self.progress_label.configure(text=phase_text)
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