import os
import uuid
import glob
import shutil
import threading
import base64
import subprocess
import webview
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import yt_dlp

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "downloads_cache")
USER_DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(USER_DOWNLOADS, exist_ok=True)


def get_base64_logo():
    logo_path = os.path.join(BASE_DIR, "icon.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
    return None


LOGO_BASE64 = get_base64_logo()
if LOGO_BASE64:
    LOGO_HTML = f'<img src="{LOGO_BASE64}" alt="Logo" class="w-10 h-10 rounded-xl border border-green-500/30 object-cover shadow-lg shadow-green-500/10">'
else:
    LOGO_HTML = '<div class="w-10 h-10 rounded-xl border border-green-500/30 bg-green-500/10 flex items-center justify-center text-green-400 font-black">PM</div>'


class DesktopAPI:
    def download_media(self, url, mode, fmt, quality, headunit):
        job_id = str(uuid.uuid4())
        template = os.path.join(TEMP_DIR, f"{job_id}_%(title).50s.%(ext)s")

        if mode == "vehicle":
            if headunit == "nszn_z66t":
                ydl_opts = {
                    'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
                    'outtmpl': template,
                    'merge_output_format': 'mp4',
                    'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
                    'postprocessor_args': [
                        '-c:v', 'libx264', '-profile:v', 'main', '-level', '4.0',
                        '-vf', 'scale=-2:720', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000'
                    ],
                    'noplaylist': True,
                    'restrictfilenames': True
                }
            elif headunit == "avic_mrz02":
                ydl_opts = {
                    'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
                    'outtmpl': template,
                    'merge_output_format': 'mp4',
                    'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
                    'postprocessor_args': [
                        '-c:v', 'libx264', '-profile:v', 'baseline', '-level', '3.0',
                        '-vf', 'scale=-2:480', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '128k', '-ar', '44100'
                    ],
                    'noplaylist': True,
                    'restrictfilenames': True
                }
            else:
                ydl_opts = {
                    'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                    'outtmpl': template,
                    'merge_output_format': 'mp4',
                    'noplaylist': True,
                    'restrictfilenames': True
                }
        else:
            if fmt == "mp3":
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': template,
                    'noplaylist': True,
                    'restrictfilenames': True,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320'
                    }]
                }
            else:
                ydl_opts = {
                    'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best',
                    'outtmpl': template,
                    'merge_output_format': 'mp4',
                    'noplaylist': True,
                    'restrictfilenames': True
                }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
        except Exception as e:
            return {"status": "error", "message": str(e)}

        files = glob.glob(os.path.join(TEMP_DIR, f"{job_id}_*"))
        if not files:
            return {"status": "error", "message": "File generation failed in temp folder."}

        temp_file = files[0]
        clean_name = os.path.basename(temp_file).replace(f"{job_id}_", "")
        dest_path = os.path.join(USER_DOWNLOADS, clean_name)

        base_name, ext = os.path.splitext(clean_name)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(USER_DOWNLOADS, f"{base_name}_{counter}{ext}")
            counter += 1

        try:
            shutil.move(temp_file, dest_path)
        except Exception as e:
            return {"status": "error", "message": f"Could not move file to Downloads: {e}"}

        return {
            "status": "ok",
            "filename": os.path.basename(dest_path),
            "path": dest_path
        }

    def open_downloads_folder(self, file_path=""):
        if file_path and os.path.exists(file_path):
            subprocess.Popen(f'explorer /select,"{file_path}"')
        else:
            os.startfile(USER_DOWNLOADS)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PureMUX v1.7</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .glass-overlay {
      position: fixed;
      inset: 0;
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.25rem;
      background: rgba(3, 5, 9, 0.85);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      transition: opacity 0.35s ease, visibility 0.35s ease;
    }
    .glass-overlay.hidden {
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
    }
  </style>
</head>
<body class="bg-gray-950 text-gray-100 flex items-center justify-center min-h-screen p-4 relative overflow-hidden select-none">

  <!-- Mandatory Terms & Conditions Disclaimer Gate -->
  <div id="disclaimerGate" class="glass-overlay">
    <div class="w-full max-w-md bg-gray-900/90 border border-green-500/30 p-6 rounded-2xl shadow-2xl shadow-green-500/10">
      <div class="inline-block text-[10px] font-bold tracking-wider px-2.5 py-1 bg-green-500/10 text-green-400 border border-green-500/30 rounded-full font-mono mb-3">
        TERMS &amp; CONDITIONS
      </div>
      <h2 class="text-xl font-bold tracking-tight text-white mb-1">Before You Continue</h2>
      <p class="text-xs text-gray-400 mb-4 leading-relaxed">
        Please review and accept the terms below to unlock access to PureMUX.
      </p>

      <div class="bg-black/40 border border-gray-800 rounded-xl p-3.5 mb-4 text-xs text-gray-300 space-y-2 leading-relaxed">
        <p><strong>Personal &amp; Authorized Use Only:</strong> This application is strictly intended for downloading media you own, created, or have explicit permission to access.</p>
        <p><strong>User Liability:</strong> You assume 100% responsibility for compliance with copyright laws and platform terms of service.</p>
        <p><strong>As-Is Software:</strong> Provided without warranties; the developer holds zero liability for misuse or damages.</p>
      </div>

      <label class="flex items-start gap-2.5 text-xs text-gray-200 cursor-pointer mb-5 select-none">
        <input type="checkbox" id="agreeCheckbox" class="mt-0.5 w-4 h-4 accent-green-500 rounded cursor-pointer" />
        <span>I accept all terms, conditions, and liability policies stated above.</span>
      </label>

      <button type="button" id="unlockBtn" disabled class="w-full py-2.5 bg-green-500 text-gray-950 font-semibold rounded-lg text-sm transition cursor-pointer shadow-lg shadow-green-500/20 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-green-500 hover:bg-green-400">
        Unlock PureMUX
      </button>
    </div>
  </div>

  <!-- Main App Container -->
  <div class="w-full max-w-md bg-gray-900 border border-gray-800 p-6 rounded-xl shadow-xl flex flex-col justify-between">
    <div>
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <!--LOGO_SLOT-->
          <div>
            <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              PureMUX <span class="text-green-400 text-[10px] px-2 py-0.5 bg-green-500/10 border border-green-500/20 rounded-full font-mono">v1.7</span>
            </h1>
            <p class="text-xs text-gray-400 mt-0.5">FFmpeg Muxer &amp; Automotive Encoder</p>
          </div>
        </div>
        <button type="button" onclick="reopenDisclaimer()" class="text-[11px] text-gray-400 hover:text-green-400 border border-gray-800 bg-gray-950 px-2.5 py-1 rounded-lg transition cursor-pointer">Disclaimer</button>
      </div>

      <!-- Mode Switcher Tabs -->
      <div class="grid grid-cols-2 gap-1 p-1 bg-gray-950 border border-gray-800 rounded-lg mb-5">
        <button type="button" id="tabStandard" onclick="setMode('standard')" class="py-1.5 text-xs font-semibold rounded-md bg-gray-800 text-green-400 transition cursor-pointer">
          Standard Media
        </button>
        <button type="button" id="tabVehicle" onclick="setMode('vehicle')" class="py-1.5 text-xs font-semibold rounded-md text-gray-400 hover:text-gray-200 transition cursor-pointer">
          Vehicle Headunit
        </button>
      </div>

      <!-- Downloader Form -->
      <form id="form" class="space-y-4">
        <div>
          <label class="block text-xs text-gray-400 mb-1 font-mono uppercase tracking-wider">Video URL</label>
          <input type="url" id="url" required placeholder="Paste video link here..." class="w-full p-2.5 bg-gray-950 border border-gray-800 rounded-lg text-sm focus:outline-none focus:border-green-500 text-gray-200 placeholder-gray-600 transition select-text">
        </div>

        <!-- Standard Options -->
        <div id="standardOptions" class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-xs text-gray-400 mb-1 font-mono uppercase tracking-wider">Format</label>
            <select id="format" class="w-full p-2.5 bg-gray-950 border border-gray-800 rounded-lg text-sm focus:outline-none focus:border-green-500 text-gray-200">
              <option value="mp4">MP4 Video</option>
              <option value="mp3">MP3 Audio (320k)</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-gray-400 mb-1 font-mono uppercase tracking-wider">Max Quality</label>
            <select id="quality" class="w-full p-2.5 bg-gray-950 border border-gray-800 rounded-lg text-sm focus:outline-none focus:border-green-500 text-gray-200">
              <option value="1080">1080p Full HD</option>
              <option value="2160">4K Ultra HD</option>
              <option value="720">720p HD</option>
            </select>
          </div>
        </div>

        <!-- Vehicle Headunit Options -->
        <div id="vehicleOptions" class="hidden space-y-2">
          <div>
            <label class="block text-xs text-gray-400 mb-1 font-mono uppercase tracking-wider">Target Headunit System</label>
            <select id="headunit" onchange="updateHeadunitHint()" class="w-full p-2.5 bg-gray-950 border border-gray-800 rounded-lg text-sm focus:outline-none focus:border-green-500 text-gray-200">
              <option value="nszn_z66t">Toyota JDM (NSZN-Z66T)</option>
              <option value="avic_mrz02">Carrozzeria Pioneer (AVIC-MRZ02)</option>
              <option value="android_screen">Android Headunit Screen</option>
            </select>
          </div>
          <p id="headunitHint" class="text-[11px] text-gray-400 bg-gray-950/60 border border-gray-800/80 p-2 rounded-lg font-mono">
            Profile: 720p MP4 (H.264 Main + AAC Stereo) for 10" JDM Display
          </p>
        </div>

        <button type="submit" id="btn" class="w-full py-2.5 bg-green-500 hover:bg-green-400 text-gray-950 font-semibold rounded-lg text-sm transition cursor-pointer shadow-lg shadow-green-500/10">Download Media</button>
      </form>

      <!-- Modern Loading Bar & Status Box -->
      <div id="statusBox" class="hidden mt-4 space-y-2">
        <div class="flex items-center justify-between gap-2 text-xs text-gray-400">
          <span id="statusText" class="truncate">Processing streams...</span>
          <button type="button" id="showFolderBtn" onclick="openSavedLocation()" class="hidden shrink-0 text-[11px] text-green-400 hover:underline font-medium cursor-pointer">
            Show in Folder
          </button>
        </div>
        <div class="w-full bg-gray-950 rounded-full h-2 overflow-hidden border border-gray-800">
          <div id="progressBar" class="bg-green-500 h-full w-full animate-pulse rounded-full"></div>
        </div>
      </div>
    </div>

    <!-- Developer Credits Footer -->
    <div class="mt-8 pt-4 border-t border-gray-800/80 text-center">
      <p class="text-xs text-gray-500">
        Created &amp; Developed by <span class="text-gray-300 font-medium">Aahil Admani</span>
      </p>
    </div>
  </div>

  <script>
    const disclaimerGate = document.getElementById('disclaimerGate');
    const agreeCheckbox = document.getElementById('agreeCheckbox');
    const unlockBtn = document.getElementById('unlockBtn');

    if (localStorage.getItem('puremux_terms_accepted') === 'true') {
      disclaimerGate.classList.add('hidden');
    }

    agreeCheckbox.addEventListener('change', function() {
      unlockBtn.disabled = !this.checked;
    });

    unlockBtn.addEventListener('click', () => {
      if (!agreeCheckbox.checked) return;
      localStorage.setItem('puremux_terms_accepted', 'true');
      disclaimerGate.classList.add('hidden');
    });

    function reopenDisclaimer() {
      agreeCheckbox.checked = false;
      unlockBtn.disabled = true;
      disclaimerGate.classList.remove('hidden');
    }

    let currentMode = 'standard';
    let lastSavedPath = '';

    const hints = {
      'nszn_z66t': 'Profile: 720p MP4 (H.264 Main + AAC Stereo) for 10" JDM Display',
      'avic_mrz02': 'Profile: 480p SD MP4 (H.264 Baseline L3.0 + AAC 44.1kHz) for older JDM hardware',
      'android_screen': 'Profile: Native 1080p MP4 (Direct high-bitrate mux for Android units)'
    };

    function setMode(mode) {
      currentMode = mode;
      const tabStandard = document.getElementById('tabStandard');
      const tabVehicle = document.getElementById('tabVehicle');
      const standardOptions = document.getElementById('standardOptions');
      const vehicleOptions = document.getElementById('vehicleOptions');

      if (mode === 'standard') {
        tabStandard.className = "py-1.5 text-xs font-semibold rounded-md bg-gray-800 text-green-400 transition cursor-pointer";
        tabVehicle.className = "py-1.5 text-xs font-semibold rounded-md text-gray-400 hover:text-gray-200 transition cursor-pointer";
        standardOptions.classList.remove('hidden');
        vehicleOptions.classList.add('hidden');
      } else {
        tabVehicle.className = "py-1.5 text-xs font-semibold rounded-md bg-gray-800 text-green-400 transition cursor-pointer";
        tabStandard.className = "py-1.5 text-xs font-semibold rounded-md text-gray-400 hover:text-gray-200 transition cursor-pointer";
        vehicleOptions.classList.remove('hidden');
        standardOptions.classList.add('hidden');
      }
    }

    function updateHeadunitHint() {
      const val = document.getElementById('headunit').value;
      document.getElementById('headunitHint').textContent = hints[val];
    }

    function openSavedLocation() {
      window.pywebview.api.open_downloads_folder(lastSavedPath);
    }

    const form = document.getElementById('form');
    const statusBox = document.getElementById('statusBox');
    const statusText = document.getElementById('statusText');
    const showFolderBtn = document.getElementById('showFolderBtn');
    const progressBar = document.getElementById('progressBar');
    const btn = document.getElementById('btn');

    form.onsubmit = async (e) => {
      e.preventDefault();

      statusBox.classList.remove('hidden');
      showFolderBtn.classList.add('hidden');
      statusText.textContent = currentMode === 'vehicle' 
        ? "Fetching & encoding for your vehicle headunit..." 
        : "Fetching high-res streams & running FFmpeg...";
      progressBar.classList.add('animate-pulse');
      progressBar.style.width = "100%";
      progressBar.style.backgroundColor = "#22c55e";
      btn.disabled = true;
      btn.classList.add('opacity-50', 'cursor-not-allowed');

      const url = document.getElementById('url').value;
      const fmt = document.getElementById('format').value;
      const quality = document.getElementById('quality').value;
      const headunit = document.getElementById('headunit').value;

      try {
        const result = await window.pywebview.api.download_media(url, currentMode, fmt, quality, headunit);

        if (result.status !== 'ok') {
          throw new Error(result.message || 'Download failed');
        }

        lastSavedPath = result.path;
        progressBar.classList.remove('animate-pulse');
        statusText.textContent = 'Saved: ' + result.filename;
        showFolderBtn.classList.remove('hidden');
      } catch (err) {
        progressBar.classList.remove('animate-pulse');
        progressBar.style.backgroundColor = '#ef4444';
        statusText.textContent = 'Error: ' + err.message;
      } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
      }
    };
  </script>
</body>
</html>
"""

HTML_PAGE = HTML_TEMPLATE.replace("<!--LOGO_SLOT-->", LOGO_HTML)


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


def run_fastapi():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_fastapi, daemon=True)
    server_thread.start()

    api = DesktopAPI()
    window = webview.create_window(
        "PureMUX v1.7",
        "http://127.0.0.1:8000",
        js_api=api,
        width=520,
        height=720,
        resizable=False,
        background_color="#030712"
    )

    icon_path = os.path.join(BASE_DIR, "icon.ico")
    if os.path.exists(icon_path):
        webview.start(icon=icon_path)
    else:
        webview.start()