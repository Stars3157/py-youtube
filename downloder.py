import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import threading
import queue
import os
import subprocess
import json
import re
import sys

# Set appearance mode and default color theme
ctk.set_appearance_mode("Dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("YouTube Downloader")
        self.geometry("1000x800")
        self.minsize(900, 700)

        # Variables
        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.speed_var = tk.StringVar(value="Speed: 0 KB/s")
        self.eta_var = tk.StringVar(value="ETA: --:--")
        self.quality_var = tk.StringVar(value="1080p")
        self.framerate_var = tk.StringVar(value="Auto")
        self.format_var = tk.StringVar(value="mp4")
        self.output_path = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.download_thread = None
        self.stop_flag = False
        self.process = None

        # Queue for thread-safe communication
        self.queue = queue.Queue()

        # Create UI
        self.create_widgets()

        # Start checking the queue
        self.after(100, self.process_queue)

        # Bind Enter key to download
        self.bind('<Return>', lambda e: self.start_download())

    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="YouTube Video Downloader",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # URL input section
        url_frame = ctk.CTkFrame(main_frame)
        url_frame.pack(fill="x", pady=(0, 15))

        url_label = ctk.CTkLabel(url_frame, text="Video URL:", font=ctk.CTkFont(size=14))
        url_label.pack(anchor="w", padx=15, pady=(15, 5))

        url_entry = ctk.CTkEntry(
            url_frame,
            textvariable=self.url_var,
            height=40,
            font=ctk.CTkFont(size=14),
            placeholder_text="Paste YouTube URL here (Ctrl+V)..."
        )
        url_entry.pack(fill="x", padx=15, pady=(0, 15))
        url_entry.focus()  # Set focus to URL entry

        # Quality, format and output section
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", pady=(0, 15))

        # Quality selection
        quality_label = ctk.CTkLabel(options_frame, text="Quality:", font=ctk.CTkFont(size=14))
        quality_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        quality_options = ["Best Quality (Highest Bitrate)", "1080p", "720p", "480p", "360p", "Audio Only"]
        quality_menu = ctk.CTkOptionMenu(
            options_frame,
            variable=self.quality_var,
            values=quality_options,
            width=200,
            font=ctk.CTkFont(size=14)
        )
        quality_menu.grid(row=0, column=1, padx=15, pady=15, sticky="w")

        # Framerate selection
        framerate_label = ctk.CTkLabel(options_frame, text="Framerate:", font=ctk.CTkFont(size=14))
        framerate_label.grid(row=0, column=2, padx=15, pady=15, sticky="w")

        framerate_options = ["Auto", "Highest", "60", "30", "24"]
        framerate_menu = ctk.CTkOptionMenu(
            options_frame,
            variable=self.framerate_var,
            values=framerate_options,
            width=100,
            font=ctk.CTkFont(size=14)
        )
        framerate_menu.grid(row=0, column=3, padx=15, pady=15, sticky="w")

        # Format selection
        format_label = ctk.CTkLabel(options_frame, text="Format:", font=ctk.CTkFont(size=14))
        format_label.grid(row=0, column=4, padx=15, pady=15, sticky="w")

        format_options = ["mp4", "webm", "mkv", "avi", "flv", "wav", "mp3", "m4a", "flac"]
        format_menu = ctk.CTkOptionMenu(
            options_frame,
            variable=self.format_var,
            values=format_options,
            width=100,
            font=ctk.CTkFont(size=14)
        )
        format_menu.grid(row=0, column=5, padx=15, pady=15, sticky="w")

        # Output location
        output_label = ctk.CTkLabel(options_frame, text="Save to:", font=ctk.CTkFont(size=14))
        output_label.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        output_path_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        output_path_frame.grid(row=1, column=1, padx=15, pady=(0, 15), sticky="ew", columnspan=3)

        output_path_entry = ctk.CTkEntry(
            output_path_frame,
            textvariable=self.output_path,
            font=ctk.CTkFont(size=14)
        )
        output_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_button = ctk.CTkButton(
            output_path_frame,
            text="Browse",
            width=80,
            command=self.browse_output_path
        )
        browse_button.pack(side="right")

        # Configure grid columns
        options_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(3, weight=1)
        options_frame.columnconfigure(5, weight=1)

        # Progress section
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", pady=(0, 15))

        # Status
        status_label = ctk.CTkLabel(
            progress_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        status_label.pack(anchor="w", padx=15, pady=(15, 5))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=25)
        self.progress_bar.pack(fill="x", padx=15, pady=5)
        self.progress_bar.set(0)

        # Speed, ETA and percentage
        progress_info_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_info_frame.pack(fill="x", padx=15, pady=(5, 15))

        speed_label = ctk.CTkLabel(
            progress_info_frame,
            textvariable=self.speed_var,
            font=ctk.CTkFont(size=12)
        )
        speed_label.pack(side="left")

        eta_label = ctk.CTkLabel(
            progress_info_frame,
            textvariable=self.eta_var,
            font=ctk.CTkFont(size=12)
        )
        eta_label.pack(side="left", padx=(20, 0))

        self.percentage_label = ctk.CTkLabel(
            progress_info_frame,
            text="0%",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.percentage_label.pack(side="right")

        # Log output
        log_label = ctk.CTkLabel(main_frame, text="Download Log:", font=ctk.CTkFont(size=14))
        log_label.pack(anchor="w", pady=(0, 5))

        self.log_text = ctk.CTkTextbox(main_frame, height=250, font=ctk.CTkFont(size=12))
        self.log_text.pack(fill="both", expand=True, pady=(0, 15))

        # Button section
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 10))

        # Fetch info button
        fetch_button = ctk.CTkButton(
            button_frame,
            text="Get Video Info",
            command=self.get_video_info,
            width=140,
            height=45,
            font=ctk.CTkFont(size=14)
        )
        fetch_button.pack(side="left", padx=(0, 10))

        # Download button - THIS IS THE BUTTON YOU WANTED
        self.download_button = ctk.CTkButton(
            button_frame,
            text="⬇️ Download",
            command=self.start_download,
            width=140,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2E7D32",  # Green color
            hover_color="#1B5E20",  # Darker green
            text_color="white"
        )
        self.download_button.pack(side="left", padx=(0, 10))

        # Stop button
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹️ Stop",
            command=self.stop_download,
            width=140,
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color="#C62828",  # Red color
            hover_color="#B71C1C",  # Darker red
            text_color="white",
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=(0, 10))

        # Clear button
        clear_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Clear",
            command=self.clear_log,
            width=100,
            height=45,
            font=ctk.CTkFont(size=14)
        )
        clear_button.pack(side="right")

        # Add keyboard shortcuts hint
        hint_label = ctk.CTkLabel(
            main_frame,
            text="Shortcuts: Enter = Download | Ctrl+V = Paste URL",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        hint_label.pack(pady=(10, 0))

    def browse_output_path(self):
        """Open file dialog to select output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_path.get())
        if directory:
            self.output_path.set(directory)
            self.log_message(f"Output directory set to: {directory}")

    def log_message(self, message):
        """Add message to log textbox"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.update_idletasks()

    def clear_log(self):
        """Clear the log textbox"""
        self.log_text.delete("1.0", "end")

    def update_progress(self, percent, speed, eta=None):
        """Update progress bar and speed display"""
        self.progress_var.set(percent / 100)
        self.progress_bar.set(percent / 100)
        self.percentage_label.configure(text=f"{percent:.1f}%")

        # Format speed display
        if speed >= 1024 * 1024:
            speed_str = f"Speed: {speed / (1024 * 1024):.1f} MB/s"
        elif speed >= 1024:
            speed_str = f"Speed: {speed / 1024:.1f} KB/s"
        else:
            speed_str = f"Speed: {speed:.1f} B/s"

        self.speed_var.set(speed_str)

        # Update ETA if provided
        if eta:
            self.eta_var.set(f"ETA: {eta}")
        else:
            self.eta_var.set("ETA: --:--")

    def get_video_info(self):
        """Fetch video information without downloading"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return

        # Check if yt-dlp is available
        if not self.check_ytdlp():
            return

        self.log_message(f"🔍 Fetching information for: {url}")
        self.status_var.set("Fetching video information...")

        # Run in thread to avoid freezing GUI
        thread = threading.Thread(target=self.fetch_info_thread, args=(url,))
        thread.daemon = True
        thread.start()

    def fetch_info_thread(self, url):
        """Thread for fetching video information"""
        try:
            # Run yt-dlp to get video info in JSON format
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-playlist",
                url
            ]

            self.queue.put(("log", f"Running command: {' '.join(cmd)}"))

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=30)

            if result.returncode == 0:
                # Parse JSON output
                video_info = json.loads(result.stdout)
                title = video_info.get('title', 'Unknown Title')
                duration = video_info.get('duration', 0)
                uploader = video_info.get('uploader', 'Unknown Uploader')
                views = video_info.get('view_count', 0)

                # Get available formats and framerates
                formats = video_info.get('formats', [])
                available_framerates = set()
                for fmt in formats:
                    fps = fmt.get('fps')
                    if fps:
                        available_framerates.add(int(fps))

                # Sort framerates in descending order
                sorted_framerates = sorted(list(available_framerates), reverse=True)

                # Format duration
                if duration:
                    mins, secs = divmod(duration, 60)
                    hrs, mins = divmod(mins, 60)
                    if hrs > 0:
                        duration_str = f"{hrs}:{mins:02d}:{secs:02d}"
                    else:
                        duration_str = f"{mins}:{secs:02d}"
                else:
                    duration_str = "Unknown"

                # Format views
                if views > 1000000:
                    views_str = f"{views / 1000000:.1f}M"
                elif views > 1000:
                    views_str = f"{views / 1000:.1f}K"
                else:
                    views_str = str(views)

                # Queue the result for GUI update
                self.queue.put(("log", "=" * 50))
                self.queue.put(("log", f"📹 Title: {title}"))
                self.queue.put(("log", f"👤 Uploader: {uploader}"))
                self.queue.put(("log", f"⏱️ Duration: {duration_str}"))
                self.queue.put(("log", f"👁️ Views: {views_str}"))

                # Display available framerates
                if sorted_framerates:
                    framerate_str = ", ".join(map(str, sorted_framerates))
                    self.queue.put(("log", f"🎬 Available Framerates: {framerate_str} fps"))
                else:
                    self.queue.put(("log", "🎬 Available Framerates: Not detected"))

                self.queue.put(("log", "✅ Video information fetched successfully!"))
                self.queue.put(("status", "Ready"))

            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                self.queue.put(("error", f"Failed to fetch video info: {error_msg}"))
                self.queue.put(("status", "Error"))

        except subprocess.TimeoutExpired:
            self.queue.put(("error", "Timeout while fetching video info"))
            self.queue.put(("status", "Error"))
        except json.JSONDecodeError:
            self.queue.put(("error", "Invalid response from YouTube"))
            self.queue.put(("status", "Error"))
        except Exception as e:
            self.queue.put(("error", f"Error fetching video info: {str(e)}"))
            self.queue.put(("status", "Error"))

    def start_download(self):
        """Start the download process - Called by Download button"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return

        # Check if yt-dlp is available
        if not self.check_ytdlp():
            return

        # Reset UI
        self.stop_flag = False
        self.progress_bar.set(0)
        self.progress_var.set(0)
        self.percentage_label.configure(text="0%")
        self.speed_var.set("Speed: 0 KB/s")
        self.eta_var.set("ETA: --:--")

        # Enable/disable buttons
        self.download_button.configure(state="disabled", fg_color="gray")
        self.stop_button.configure(state="normal")

        # Start download in thread
        self.download_thread = threading.Thread(target=self.download_thread_func, args=(url,))
        self.download_thread.daemon = True
        self.download_thread.start()

    def download_thread_func(self, url):
        """Thread for downloading video"""
        try:
            # Build command based on quality selection
            cmd = self.build_download_command(url)

            self.queue.put(("log", "=" * 50))
            self.queue.put(("log", f"🚀 Starting download: {url}"))
            self.queue.put(("log", f"⚙️ Quality: {self.quality_var.get()}"))
            self.queue.put(("log", f"🎬 Framerate: {self.framerate_var.get()}"))
            self.queue.put(("log", f"📦 Format: {self.format_var.get()}"))
            self.queue.put(("log", f"📁 Output: {self.output_path.get()}"))
            self.queue.put(("status", "Downloading..."))

            # Start the process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )

            # Parse output in real-time
            if self.process.stdout:
                for line in iter(self.process.stdout.readline, ''):
                    if self.stop_flag:
                        self.process.terminate()
                        break

                    # Parse progress information
                    self.parse_progress(line)

                    # Send line to queue for GUI update
                    if line.strip():
                        self.queue.put(("log", line.strip()))

                # Wait for process to complete
                self.process.stdout.close()
            return_code = self.process.wait()

            if self.stop_flag:
                self.queue.put(("log", "⏹️ Download stopped by user"))
                self.queue.put(("status", "Stopped"))
            elif return_code == 0:
                self.queue.put(("log", "✅ Download completed successfully!"))
                self.queue.put(("status", "Completed"))
                self.queue.put(("progress", (100, 0)))  # 100% complete
            else:
                self.queue.put(("log", f"❌ Download failed with code: {return_code}"))
                self.queue.put(("status", "Failed"))

        except Exception as e:
            self.queue.put(("error", f"Download error: {str(e)}"))
            self.queue.put(("status", "Error"))

        finally:
            # Re-enable download button
            self.queue.put(("reset_buttons", None))

    def build_download_command(self, url):
        """Build yt-dlp command based on user selection"""
        output_template = os.path.join(self.output_path.get(), '%(title)s.%(ext)s')

        # Base command
        cmd = ["yt-dlp", "-o", output_template, "--newline", "--progress"]

        # Add quality options
        quality = self.quality_var.get()
        framerate = self.framerate_var.get()
        format_ext = self.format_var.get()

        # Build format string based on framerate selection
        if framerate == "Highest":
            framerate_filter = "[fps>30]"  # Prefer higher than 30fps
        elif framerate == "60":
            framerate_filter = "[fps=60]"
        elif framerate == "30":
            framerate_filter = "[fps=30]"
        elif framerate == "24":
            framerate_filter = "[fps=24]"
        else:  # Auto
            framerate_filter = ""

        if quality == "Best Quality (Highest Bitrate)":
            if format_ext in ["mp3", "wav", "m4a", "flac"]:
                cmd.extend(["-f", "bestaudio", "-x", "--audio-format", format_ext])
            else:
                if framerate_filter:
                    cmd.extend(["-f", f"bestvideo{framerate_filter}+bestaudio/best{framerate_filter}"])
                else:
                    cmd.extend(["-f", "best"])
        elif quality == "Audio Only":
            cmd.extend(["-f", "bestaudio", "-x", "--audio-format", "mp3"])
        else:
            # For specific resolutions, try to get the best video with that resolution
            resolution = quality.replace("p", "")
            if format_ext in ["mp3", "wav", "m4a", "flac"]:
                cmd.extend(["-f", "bestaudio", "-x", "--audio-format", format_ext])
            else:
                if framerate_filter:
                    cmd.extend(["-f",
                                f"bestvideo[height<={resolution}]{framerate_filter}+bestaudio/best[height<={resolution}]{framerate_filter}"])
                else:
                    cmd.extend(["-f", f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]"])

        # Add URL
        cmd.append(url)

        return cmd

    def parse_progress(self, line):
        """Parse yt-dlp output for progress information"""
        # Try to extract percentage
        percent_match = re.search(r'(\d+\.?\d*)%', line)
        if percent_match:
            percent = float(percent_match.group(1))

            # Try to extract download speed
            speed = 0
            speed_match = re.search(r'(\d+\.?\d*)([KM]?)iB/s', line)
            if speed_match:
                speed_value = float(speed_match.group(1))
                unit = speed_match.group(2)

                # Convert to KB/s
                if unit == 'M':
                    speed = speed_value * 1024
                elif unit == 'K':
                    speed = speed_value
                else:
                    speed = speed_value / 1024

            # Try to extract ETA
            eta = None
            eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
            if eta_match:
                eta = eta_match.group(1)

            # Update progress in GUI via queue
            self.queue.put(("progress", (percent, speed, eta)))

    def stop_download(self):
        """Stop the current download"""
        self.stop_flag = True
        self.status_var.set("Stopping...")
        self.log_message("🛑 Stopping download...")
        if self.process:
            self.process.terminate()

    def check_ytdlp(self):
        """Check if yt-dlp is installed and available"""
        try:
            result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.queue.put(("log", f"✅ yt-dlp version: {version}"))
                return True
            else:
                self.queue.put(("error", "yt-dlp not found or not working properly!"))
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            self.queue.put(("error", "yt-dlp not found! Please install yt-dlp first."))
            self.queue.put(("error", "Install with: pip install yt-dlp"))
            self.queue.put(("error", "Or download from: https://github.com/yt-dlp/yt-dlp"))
            return False

    def process_queue(self):
        """Process messages from the queue (thread-safe GUI updates)"""
        try:
            while True:
                msg_type, data = self.queue.get_nowait()

                if msg_type == "log":
                    self.log_message(data)
                elif msg_type == "info":
                    self.log_message(f"ℹ️ {data}")
                elif msg_type == "error":
                    self.log_message(f"❌ ERROR: {data}")
                    messagebox.showerror("Error", data)
                elif msg_type == "status":
                    self.status_var.set(data)
                elif msg_type == "progress":
                    if len(data) == 2:
                        percent, speed = data
                        self.update_progress(percent, speed)
                    elif len(data) == 3:
                        percent, speed, eta = data
                        self.update_progress(percent, speed, eta)
                elif msg_type == "reset_buttons":
                    self.download_button.configure(state="normal", fg_color="#2E7D32")
                    self.stop_button.configure(state="disabled")

        except queue.Empty:
            pass

        # Schedule next queue check
        self.after(100, self.process_queue)


# Installation instructions
def show_installation_guide():
    """Show installation guide if dependencies are missing"""
    import sys
    print("=" * 60)
    print("YouTube Downloader Installation Guide")
    print("=" * 60)
    print("\nRequired dependencies:")
    print("1. yt-dlp - for downloading videos")
    print("2. customtkinter - for modern GUI")
    print("\nInstall with:")
    print("pip install yt-dlp customtkinter")
    print("\nOr install individually:")
    print("pip install yt-dlp")
    print("pip install customtkinter")
    print("\nOn some systems, you might need:")
    print("pip install --upgrade yt-dlp")
    print("=" * 60)


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import customtkinter
    except ImportError:
        show_installation_guide()
        print("\nCustomTkinter not installed. Attempting to install...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
            import customtkinter

            print("CustomTkinter installed successfully!")
        except:
            print("Failed to install CustomTkinter. Please install manually.")
            sys.exit(1)

    # Check for yt-dlp
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        show_installation_guide()
        print("\nyt-dlp not found. Please install it using:")
        print("pip install yt-dlp")
        print("\nThe app will still open, but downloads won't work without yt-dlp.")

    # Create and run app
    app = YouTubeDownloaderApp()
    app.mainloop()