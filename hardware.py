import psutil
import time
import sys
import os

# --- 1. SENSOR CLASS ---
class Sensor:
    def __init__(self, key, default_title, unit, data_function, color="gray"):
        self.key = key
        self.default_title = default_title
        self.unit = unit
        self.func = data_function
        self.color = color

    def get_value(self):
        return self.func()

# --- 2. LOAD HARDWARE LIBRARY (DLL) ---
computer = None
try:
    import clr 
    
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    dll_path = os.path.join(base_path, "LibreHardwareMonitorLib.dll")
    
    if os.path.exists(dll_path):
        clr.AddReference(dll_path)
        from LibreHardwareMonitor.Hardware import Computer # type: ignore
        
        computer = Computer()
        computer.IsCpuEnabled = True  
        computer.IsGpuEnabled = True  
        computer.IsMemoryEnabled = True 
        computer.IsMotherboardEnabled = True 
        computer.Open()
        print("HARDWARE MONITOR ENGINE LOADED SUCCESSFULLY!")
    else:
        print(f"WARNING: File not found: {dll_path}")

except Exception as e:
    print(f"WARNING: Could not load DLL (Error: {e})")


# --- 3. HELPER FUNCTIONS ---
def get_sensor_value(hardware_type_filter, sensor_type, sensor_name_part=""):
    if not computer: return "N/A"

    try:
        for hardware in computer.Hardware:
            hardware.Update()
            if hardware_type_filter.lower() in str(hardware.HardwareType).lower():
                for sensor in hardware.Sensors:
                    if str(sensor.SensorType) == sensor_type:
                        if sensor_name_part and sensor_name_part.lower() not in sensor.Name.lower():
                            continue
                        if sensor.Value is not None:
                            return round(sensor.Value, 1)
    except:
        pass
    return "N/A"

# --- 4. DATA SOURCES ---

def get_cpu_temp():
    val = get_sensor_value("Cpu", "Temperature", "Package")
    if val == "N/A": val = get_sensor_value("Cpu", "Temperature", "Core")
    if val == "N/A": val = get_sensor_value("Cpu", "Temperature", "Tdie")
    if val == "N/A": val = get_sensor_value("Cpu", "Temperature", "")
    return val

def get_cpu_load():
    val = get_sensor_value("Cpu", "Load", "Total")
    if val == "N/A": return psutil.cpu_percent(interval=0)
    return val

def get_gpu_temp():
    return get_sensor_value("Gpu", "Temperature", "")

def get_gpu_data():
    core = get_sensor_value("Gpu", "Load", "Core")
    if core == "N/A": core = 0
    
    vram_mb = get_sensor_value("Gpu", "SmallData", "Memory Used")
    if vram_mb == "N/A": vram_mb = get_sensor_value("Gpu", "SmallData", "Memory")
    if vram_mb == "N/A": vram_mb = get_sensor_value("Gpu", "SmallData", "Dedicated")
    
    if vram_mb == "N/A": vram_mb = 0
    
    return {
        "core": core,
        "vram_gb": round(vram_mb / 1024, 1)
    }

def get_ram_data():
    mem = psutil.virtual_memory()
    return {
        "percent": mem.percent,
        "gb": round(mem.used / (1024**3), 1)
    }

def get_net_speed():
    global last_net_io, last_time
    current_net_io = psutil.net_io_counters()
    current_time = time.time()
    
    bytes_sent = current_net_io.bytes_sent - last_net_io.bytes_sent
    bytes_recv = current_net_io.bytes_recv - last_net_io.bytes_recv
    
    duration = current_time - last_time
    if duration <= 0: return 0 

    mb_per_sec = ((bytes_sent + bytes_recv) / 1024 / 1024) / duration
    last_net_io = current_net_io
    last_time = current_time
    return round(mb_per_sec, 2)

last_net_io = psutil.net_io_counters()
last_time = time.time()

# --- 5. SENSOR LIST ---
sensor_list = [
    Sensor("cpu", "CPU LOAD", "%", get_cpu_load, "text-red-500"),
    Sensor("cpu_temp", "CPU TEMP", "°C", get_cpu_temp, "text-red-300"),
    Sensor("gpu", "GPU LOAD", "%", get_gpu_data, "text-green-500"),
    Sensor("gpu_temp", "GPU TEMP", "°C", get_gpu_temp, "text-green-300"),
    Sensor("ram", "RAM LOAD", "%", get_ram_data, "text-yellow-500"),
    Sensor("net", "NET I/O", "MB/s", get_net_speed, "text-blue-500"),
]