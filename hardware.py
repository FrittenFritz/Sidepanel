import psutil
import time
import sys
import os
import subprocess # Required for WMI fallback

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
    
    # Determine execution path (script vs. frozen exe)
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Path to main library
    dll_path = os.path.join(base_path, "LibreHardwareMonitorLib.dll")
    
    # HidSharp is loaded automatically by CLR if present in the same folder.
    # We just ensure it exists physically to prevent runtime crashes.
    hid_path = os.path.join(base_path, "HidSharp.dll")
    
    if os.path.exists(dll_path):
        clr.AddReference(dll_path)
        from LibreHardwareMonitor.Hardware import Computer # type: ignore
        
        computer = Computer()
        computer.IsCpuEnabled = True  
        computer.IsGpuEnabled = True  
        computer.IsMemoryEnabled = True 
        computer.IsMotherboardEnabled = True 
        computer.IsControllerEnabled = True # Important for AIOs/Fan Controllers
        computer.Open()
        # print("HARDWARE MONITOR ENGINE LOADED SUCCESSFULLY!")
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
            
            # Check main hardware and sub-hardware (e.g. SuperIO chips)
            check_list = [hardware]
            if hasattr(hardware, "SubHardware"):
                check_list.extend(hardware.SubHardware)

            for hw_item in check_list:
                hw_item.Update()
                # Case-insensitive check for hardware type
                if hardware_type_filter.lower() in str(hw_item.HardwareType).lower():
                    for sensor in hw_item.Sensors:
                        if str(sensor.SensorType) == sensor_type:
                            # Optional: Filter by name
                            if sensor_name_part and sensor_name_part.lower() not in sensor.Name.lower():
                                continue
                            
                            # CRITICAL: Only return valid values > 0 to avoid ghost readings
                            if sensor.Value is not None and sensor.Value > 0:
                                return round(sensor.Value, 1)
    except:
        pass
    return "N/A"

# --- FALLBACK: WMI (PowerShell) ---
def get_wmi_temp():
    """ Queries Windows via PowerShell if DLL access is blocked by security features (Core Isolation) """
    try:
        cmd = "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature"
        
        # Suppress console window for subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", cmd], 
            startupinfo=startupinfo,
            creationflags=0x08000000
        ).decode().strip()
        
        # Parse output (Windows often returns multiple values)
        lines = output.split('\r\n')
        for line in lines:
            if line.isdigit():
                kelvin = int(line)
                # Windows returns tenths of Kelvin (e.g. 3100 = 310.0 Kelvin)
                celsius = (kelvin / 10.0) - 273.15
                # Plausibility check
                if celsius > 20 and celsius < 110: 
                    return round(celsius, 1)
    except:
        pass
    return 0

# --- 4. DATA SOURCES ---

def get_cpu_temp():
    # 1. Try DLL (Most precise)
    val = get_sensor_value("Cpu", "Temperature", "Tctl/Tdie") # Ryzen Standard
    if val != "N/A" and val > 0: return val

    val = get_sensor_value("Cpu", "Temperature", "Package") # Intel Standard
    if val != "N/A" and val > 0: return val
    
    val = get_sensor_value("Cpu", "Temperature", "Core")
    if val != "N/A" and val > 0: return val

    val = get_sensor_value("Cpu", "Temperature", "") # Any CPU Temp
    if val != "N/A" and val > 0: return val
    
    # 2. Try Motherboard Sensors (SuperIO)
    val = get_sensor_value("SuperIO", "Temperature", "CPU")
    if val != "N/A" and val > 0: return val

    # 3. LAST RESORT: Windows WMI (Fallback)
    return get_wmi_temp()

def get_cpu_load():
    val = get_sensor_value("Cpu", "Load", "Total")
    if val == "N/A": return psutil.cpu_percent(interval=0)
    return val

def get_gpu_temp():
    val = get_sensor_value("Gpu", "Temperature", "")
    if val == "N/A": return 0
    return val

def get_gpu_data():
    core = get_sensor_value("Gpu", "Load", "Core")
    if core == "N/A": core = 0
    
    # Try various memory sensor names
    vram_mb = get_sensor_value("Gpu", "SmallData", "Memory Used")
    if vram_mb == "N/A": vram_mb = get_sensor_value("Gpu", "SmallData", "Memory")
    if vram_mb == "N/A": vram_mb = get_sensor_value("Gpu", "SmallData", "Dedicated")
    
    if vram_mb == "N/A": vram_mb = 0
    
    return {
        "core": core,
        "vram_gb": round(vram_mb / 1024, 1) # Convert MB to GB
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

# Initialize globals for network calculation
last_net_io = psutil.net_io_counters()
last_time = time.time()

# --- 5. SENSOR LIST ---
# These default titles act as keys for translation in the frontend
sensor_list = [
    Sensor("cpu", "CPU LOAD", "%", get_cpu_load, "text-red-500"),
    Sensor("cpu_temp", "CPU TEMP", "°C", get_cpu_temp, "text-red-300"),
    Sensor("gpu", "GPU LOAD", "%", get_gpu_data, "text-green-500"),
    Sensor("gpu_temp", "GPU TEMP", "°C", get_gpu_temp, "text-green-300"),
    Sensor("ram", "RAM LOAD", "%", get_ram_data, "text-yellow-500"),
    Sensor("net", "NET I/O", "MB/s", get_net_speed, "text-blue-500"),
]

def cleanup():
    global computer
    if computer:
        try:
            computer.Close()
        except:
            pass