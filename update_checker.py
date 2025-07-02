import customtkinter as ctk
import webbrowser

def create_update_content(root):
    # إطار لتوسيط المحتوى
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(expand=True)

    # عنوان في الأعلى
    title_label = ctk.CTkLabel(main_frame, text="Update Section - قسم التحديث",
                               font=("Arial", 20, "bold"), text_color="white")
    title_label.pack(pady=10)

    # نص بالإنجليزية والعربية
    english_text = "This application requires a mandatory update every month to ensure libraries are up-to-date. Without updates, the download feature will not work."
    arabic_text = "هذا التطبيق يتطلب تحديثًا إجباريًا شهريًا تقريبا لضمان تحديث المكتبات \n بدون التحديث، ميزة التحميل لن تعمل"

    # تسمية النصوص
    english_label = ctk.CTkLabel(main_frame, text=english_text, font=("Arial", 18), wraplength=500, justify="center")
    arabic_label = ctk.CTkLabel(main_frame, text=arabic_text, font=("Arial", 18), wraplength=500, justify="center")

    # ترتيب النصوص
    english_label.pack(pady=20)
    arabic_label.pack(pady=20)

    # الإصدار الحالي
    version_label = ctk.CTkLabel(main_frame, text="Current Version: 3.1 | Check for the latest version \n الإصدار الحالي: 3.1 | تحقق من أحدث إصدار",
                                 font=("Arial", 16), text_color="gray")
    version_label.pack(pady=20)

    # زر لفتح الرابط
    def open_github():
        webbrowser.open("https://github.com/harizhammouda/YouTubeDownloaderApp?tab=readme-ov-file#-download-executable")

    update_button = ctk.CTkButton(main_frame, text="Check for Updates\nتحقق من التحديثات",
                                  command=open_github , font=("Arial", 16))
    update_button.pack(pady=15)

    # توسيط الإطار
    main_frame.place(relx=0.5, rely=0.5, anchor="center")

    return main_frame

if __name__ == "__main__":
    root = ctk.CTk()
    create_update_content(root)
    root.mainloop()