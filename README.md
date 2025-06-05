# 🎥 YouTube Downloader App 📥

Welcome to the **YouTube Downloader App**! 🚀 This is a simple yet powerful Python application built to download YouTube videos and audio files with an easy-to-use interface. Whether you're a content creator or just love saving your favorite videos, this app has got you covered! 😄

![YouTube Downloader Logo](https://raw.githubusercontent.com/harizhammouda/YouTubeDownloaderApp/refs/heads/master/img/download.ico) <!-- استبدل هذا برابط صورة لشعارك (مثل download.ico كـ PNG) -->

## 🌟 Features
- Download YouTube videos in MP4 format with customizable quality. 🎬
- Extract audio from videos in MP3 format. 🎵
- Send debug logs and user ideas to improve the app. 📧
- User-friendly interface built with `customtkinter`. 🖥️
- Support for multiple languages (English/Arabic). 🌐

## 🛠️ Technologies and Libraries Used
This project relies on the following Python libraries:
- **`customtkinter`**: For creating a modern, dark-themed GUI. 🌙
- **`yt-dlp`**: To handle YouTube video and audio downloads. 📹
- **`requests`**: For sending debug logs and ideas via Telegram API. 📤
- **`subprocess`**: To execute external commands (e.g., ffmpeg). ⚙️
- **`threading`**: For running downloads in the background. ⏳
- **`webbrowser`**: To open the website link. 🌐
- **`os` and `pathlib`**: For file handling and logging. 📂
- **`ffmpeg`**: For merging video and audio files (included as an executable). 🎞️

### Requirements
- Python 3.8+
- Install dependencies using:
  ```bash
  pip install customtkinter yt-dlp requests
