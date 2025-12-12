from flask import Flask, render_template, jsonify, request
from hardware import sensor_list, cleanup
import socket
import json
import os
import sys
import threading
import time
import webbrowser
from PIL import Image
import pystray
import logging

# --- VERSION ---
VERSION = "v0.9.3"

# --- CONFIGURATION ---
CONFIG_FILE = 'config.json'

DEFAULT_CONFIG = {
    "show_advanced_colors": False,
    "colors": {
        "bg_body": "#1c1c1c",
        "bg_card": "#262626",
        "text_title": "#dedede",
        "text_button": "#dedede",
        "text_primary": "#dedede",
        "text_secondary": "#dedede",
        "accent_cpu": "#ef4444",
        "accent_gpu": "#22c55e",
        "accent_ram": "#eab308",
        "accent_net": "#3b82f6"
    },
    "order": ["cpu", "cpu_temp", "gpu", "gpu_temp", "ram", "net"],
    "graph_order": ["graph-cpu", "graph-gpu", "graph-ram", "graph-net"],
    "custom_widths": {},
    "sensor_modes": {},
    "refresh_rate": 1000,
    "card_size": "medium",
    "language": "en"
    
}

# --- GLOBAL DATA CACHE ---
current_data = {}

def update_sensor_loop():
    """ Background thread: Polls hardware continuously to prevent request lag """
    while True:
        try:
            for sensor in sensor_list:
                current_data[sensor.key] = sensor.get_value()
        except Exception as e:
            print(f"Error in update loop: {e}")
        time.sleep(0.1) 

# --- HELPERS ---
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_config_path():
    """ Config is always stored next to the executable """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, CONFIG_FILE)

def load_config():
    path = get_config_path()
    if not os.path.exists(path):
        # FIX: If file is missing, create it immediately with default values
        try:
            with open(path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
        except Exception as e:
            print(f"Error creating config file: {e}")
        return DEFAULT_CONFIG
        
    try:
        with open(path, 'r') as f:
            cfg = json.load(f)
            # Apply defaults for potentially missing keys in old configs
            if "show_advanced_colors" not in cfg: cfg["show_advanced_colors"] = False
            if "refresh_rate" not in cfg: cfg["refresh_rate"] = 1000
            if "card_size" not in cfg: cfg["card_size"] = "medium"
            if "language" not in cfg: cfg["language"] = "en"
            if "custom_widths" not in cfg: cfg["custom_widths"] = {}
            if "graph_order" not in cfg: cfg["graph_order"] = ["graph-cpu", "graph-gpu", "graph-ram", "graph-net"]
            
            if "colors" in cfg:
                if "text_title" not in cfg["colors"]: cfg["colors"]["text_title"] = "#38bdf8"
                if "text_button" not in cfg["colors"]: cfg["colors"]["text_button"] = "#dedede"
            
            return cfg
    except:
        return DEFAULT_CONFIG

def save_config(new_config):
    path = get_config_path()
    with open(path, 'w') as f:
        json.dump(new_config, f, indent=4)

# --- FLASK SETUP ---
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__)

# Suppress Flask CLI logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template('dashboard.html', sensors=sensor_list, version=VERSION)

@app.route('/api/data')
def get_data():
    return jsonify(current_data)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(load_config())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    new_settings = request.json
    save_config(new_settings)
    return jsonify({"status": "success"})

# --- TRAY ICON ---
def run_tray_icon(url):
    def on_open(icon, item):
        webbrowser.open(url)
    def on_exit(icon, item):
        icon.stop()
        cleanup()  # <--- IMPORTANT: Disconnects hardware here
        os._exit(0)

    image_path = get_resource_path("pulse_chip.ico")
    try:
        image = Image.open(image_path)
    except:
        image = Image.new('RGB', (64, 64), color = (0, 255, 255))

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", on_open, default=True),
        pystray.MenuItem("Exit", on_exit)
    )
    # Icon tooltip shows version
    icon = pystray.Icon("Sidepanel", image, f"Sidepanel Server {VERSION}", menu)
    icon.run()

if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    dashboard_url = f"http://{local_ip}:5000"
    print(f"Server running! Dashboard: {dashboard_url} ({VERSION})")

    # Start background polling
    polling_thread = threading.Thread(target=update_sensor_loop)
    polling_thread.daemon = True
    polling_thread.start()

    # Start Flask server
    server_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False))
    server_thread.daemon = True
    server_thread.start()

    # Start Tray Icon (Main thread)
    run_tray_icon(dashboard_url)