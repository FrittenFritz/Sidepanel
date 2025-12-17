import psutil
import time
import sys
import os
import subprocess

# --- 1. SENSOR CLASS ---
class Sensor:
    def __init__(self, key, default_title, unit, data_source_key, color="gray"):
        self.key = key
        self.default_title = default_title
        self.unit = unit
        self.source_key = data_source_key # Key for the monitor source
        self.color = color

# --- 2. HARDWARE MONITOR ENGINE ---
class HardwareMonitor:
    def __init__(self):
        self.computer = None
        self.hardware_list = [] # List of active hardware components (for Update())
        self.sensor_pointers = {} # Map: 'cpu_temp' -> SensorObject
        self.dll_loaded = False
        
        # Network cache
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()

        self._load_dll()
        if self.dll_loaded:
            self._init_sensors()

    def _load_dll(self):
        try:
            import clr 
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            dll_path = os.path.join(base_path, "LibreHardwareMonitorLib.dll")
            
            if os.path.exists(dll_path):
                clr.AddReference(dll_path)
                from LibreHardwareMonitor.Hardware import Computer  # type: ignore
                self.computer = Computer()
                self.computer.IsCpuEnabled = True  
                self.computer.IsGpuEnabled = True  
                self.computer.IsMemoryEnabled = True 
                self.computer.IsMotherboardEnabled = True 
                self.computer.IsControllerEnabled = True
                self.computer.Open()
                self.dll_loaded = True
            else:
                print(f"WARNING: DLL not found at {dll_path}")
        except Exception as e:
            print(f"WARNING: Could not load DLL: {e}")

    def _find_sensor(self, hardware_type, sensor_type, name_filter=None):
        """ Helper function: Searches for a specific sensor in the hardware tree """
        if not self.computer: return None
        
        # Search hardware
        for hw in self.computer.Hardware:
            if hardware_type.lower() in str(hw.HardwareType).lower():
                hw.Update() # One-time update to find sensors
                
                # Check SubHardware (e.g., SuperIO)
                targets = [hw]
                targets.extend(hw.SubHardware)

                for target in targets:
                    target.Update()
                    for sensor in target.Sensors:
                        if str(sensor.SensorType) == sensor_type:
                            if name_filter and name_filter.lower() not in sensor.Name.lower():
                                continue
                            
                            # If found, add hardware to update list (if not already present)
                            if target not in self.hardware_list:
                                self.hardware_list.append(target)
                            return sensor
        return None

    def _init_sensors(self):
        print("Initializing Sensors (One-time scan)...")
        
        # 1. CPU LOAD (Total)
        self.sensor_pointers['cpu_load'] = self._find_sensor('Cpu', 'Load', 'Total')
        
        # 2. CPU TEMP (Try various sources)
        cpu_temp = self._find_sensor('Cpu', 'Temperature', 'Tctl') or \
                   self._find_sensor('Cpu', 'Temperature', 'Package') or \
                   self._find_sensor('Cpu', 'Temperature', 'Core') or \
                   self._find_sensor('SuperIO', 'Temperature', 'CPU')
        self.sensor_pointers['cpu_temp'] = cpu_temp

        # 3. GPU LOAD
        self.sensor_pointers['gpu_load'] = self._find_sensor('Gpu', 'Load', 'Core')

        # 4. GPU TEMP
        self.sensor_pointers['gpu_temp'] = self._find_sensor('Gpu', 'Temperature', '')

        # 5. GPU VRAM (Try various names)
        gpu_mem = self._find_sensor('Gpu', 'SmallData', 'Memory Used') or \
                  self._find_sensor('Gpu', 'SmallData', 'Memory') or \
                  self._find_sensor('Gpu', 'SmallData', 'Dedicated')
        self.sensor_pointers['gpu_mem'] = gpu_mem
        
        print(f"Sensors found: {list(self.sensor_pointers.keys())}")

    def update_hardware(self):
        """ Called in loop: Updates only relevant hardware components """
        if self.dll_loaded:
            for hw in self.hardware_list:
                hw.Update()

    def get_value(self, key):
        # Special case: RAM (psutil is more efficient/simpler)
        if key == 'ram':
            mem = psutil.virtual_memory()
            return {"percent": int(mem.percent), "gb": round(mem.used / (1024**3), 1)}
        
        # Special case: Network (psutil)
        if key == 'net':
            now = time.time()
            io = psutil.net_io_counters()
            duration = now - self.last_net_time
            if duration <= 0: return 0
            
            bytes_sent = io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = io.bytes_recv - self.last_net_io.bytes_recv
            mb_per_sec = ((bytes_sent + bytes_recv) / 1024 / 1024) / duration
            
            self.last_net_io = io
            self.last_net_time = now
            return round(mb_per_sec, 2)

        # Standard DLL sensors
        if key in self.sensor_pointers and self.sensor_pointers[key]:
            val = self.sensor_pointers[key].Value
            if val is not None:
                if key == 'gpu_mem': return round(val / 1024, 1) # MB -> GB
                if key == 'gpu_load': 
                    # GPU data return object
                    vram = 0
                    if 'gpu_mem' in self.sensor_pointers and self.sensor_pointers['gpu_mem']:
                        v = self.sensor_pointers['gpu_mem'].Value
                        if v: vram = round(v / 1024, 1)
                    return {"core": int(val), "vram_gb": vram}
                
                return int(round(val))
        
        # Fallbacks if DLL sensor is missing
        if key == 'cpu_load': return int(psutil.cpu_percent(interval=0))
        if key == 'cpu_temp': return self._get_wmi_temp() # Fallback WMI
        if key == 'gpu_load': return {"core": 0, "vram_gb": 0}
        
        return 0

    def _get_wmi_temp(self):
        """ Fallback for CPU Temp """
        try:
            cmd = "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature"
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], startupinfo=startupinfo, creationflags=0x08000000).decode().strip()
            lines = output.split('\r\n')
            for line in lines:
                if line.isdigit():
                    c = (int(line) / 10.0) - 273.15
                    if 20 < c < 110: return int(round(c))
        except:
            pass
        return 0
    
    def cleanup(self):
        if self.computer:
            try: self.computer.Close()
            except: pass

# --- 3. INSTANCE & API ---
monitor = HardwareMonitor()

def get_data_for_api():
    monitor.update_hardware() # Refresh hardware state
    return {
        "cpu": monitor.get_value('cpu_load'),
        "cpu_temp": monitor.get_value('cpu_temp'),
        "gpu": monitor.get_value('gpu_load'),
        "gpu_temp": monitor.get_value('gpu_temp'),
        "ram": monitor.get_value('ram'),
        "net": monitor.get_value('net')
    }

def cleanup():
    monitor.cleanup()

# Definition for frontend generation (colors etc.)
sensor_list = [
    Sensor("cpu", "CPU LOAD", "%", "cpu", "text-red-500"),
    Sensor("cpu_temp", "CPU TEMP", "°C", "cpu_temp", "text-red-300"),
    Sensor("gpu", "GPU LOAD", "%", "gpu", "text-green-500"),
    Sensor("gpu_temp", "GPU TEMP", "°C", "gpu_temp", "text-green-300"),
    Sensor("ram", "RAM LOAD", "%", "ram", "text-yellow-500"),
    Sensor("net", "NET I/O", "MB/s", "net", "text-blue-500"),
]