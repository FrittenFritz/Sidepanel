from flask import Flask, render_template, jsonify, request
from hardware import sensor_list, get_data_for_api, cleanup
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
VERSION = "v0.9.5" # Optimized

# --- CONFIGURATION ---
CONFIG_FILE = 'config.json'
data_lock = threading.Lock() # Thread safety

DEFAULT_CONFIG = {
    "show_advanced_colors": False,
    "colors": {
        "bg_body": "#1c1c1c", "bg_card": "#262626",
        "text_title": "#dedede", "text_button": "#dedede",
        "text_primary": "#dedede", "text_secondary": "#dedede",
        "accent_cpu": "#ef4444", "accent_gpu": "#22c55e",
        "accent_ram": "#eab308", "accent_net": "#3b82f6"
    },
    "order": ["cpu", "cpu_temp", "gpu", "gpu_temp", "ram", "net"],
    "graph_order": ["graph-cpu", "graph-gpu", "graph-ram", "graph-net"],
    "custom_widths": {}, "sensor_modes": {},
    "refresh_rate": 1000, "card_size": "medium", "language": "en"
}

# --- GLOBAL DATA CACHE ---
current_data = {}

def update_sensor_loop():
    """ Background thread: Updates hardware data securely """
    while True:
        try:
            # Fetches all data in one go from the optimized hardware class
            new_data = get_data_for_api()
            
            with data_lock:
                global current_data
                current_data = new_data
                
        except Exception as e:
            print(f"Error in update loop: {e}")
        
        # 0.5s is sufficient for smooth updates and saves CPU
        time.sleep(0.5) 

# --- HELPERS ---
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_config_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, CONFIG_FILE)

def load_config():
    path = get_config_path()
    if not os.path.exists(path):
        try:
            with open(path, 'w') as f: json.dump(DEFAULT_CONFIG, f, indent=4)
        except: pass
        return DEFAULT_CONFIG
    try:
        with open(path, 'r') as f:
            cfg = json.load(f)
            # Merge defaults
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg: cfg[k] = v
            return cfg
    except:
        return DEFAULT_CONFIG

def save_config(new_config):
    path = get_config_path()
    with open(path, 'w') as f: json.dump(new_config, f, indent=4)

def get_ip_address():
    """ Robust method to determine the actual network IP """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # connect doesn't send data, just determines the interface route
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# --- FLASK SETUP ---
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template('dashboard.html', sensors=sensor_list, version=VERSION)

@app.route('/api/data')
def get_data():
    with data_lock:
        return jsonify(current_data)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(load_config())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    save_config(request.json)
    return jsonify({"status": "success"})

# --- TRAY ICON ---
def run_tray_icon(url):
    def on_open(icon, item): webbrowser.open(url)
    def on_exit(icon, item):
        icon.stop()
        cleanup()
        os._exit(0)

    image_path = get_resource_path("pulse_chip.ico")
    try: image = Image.open(image_path)
    except: image = Image.new('RGB', (64, 64), color = (0, 255, 255))

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", on_open, default=True),
        pystray.MenuItem("Exit", on_exit)
    )
    icon = pystray.Icon("Sidepanel", image, f"Sidepanel {VERSION}", menu)
    icon.run()

if __name__ == '__main__':
    local_ip = get_ip_address()
    dashboard_url = f"http://{local_ip}:5000"
    print(f"Server running! Dashboard: {dashboard_url} ({VERSION})")

    t = threading.Thread(target=update_sensor_loop)
    t.daemon = True
    t.start()

    server = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False))
    server.daemon = True
    server.start()

    run_tray_icon(dashboard_url)