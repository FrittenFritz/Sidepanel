# Sidepanel

**A lightweight, customizable hardware monitor dashboard designed for second screens.**

![Sidepanel Icon](pulse_chip.ico)

**Sidepanel** converts any device with a browser (Tablet, Smartphone, Laptop) into a dedicated hardware monitoring display for your PC. It is designed to be extremely resource-efficient, customizable, and bloat-free.

---

## 🚀 Features

* **Real-Time Monitoring:** View CPU, GPU, RAM, and Network usage/temperatures instantly.
* **Interactive Graphs:** Track the history of your hardware performance (1-minute window).
* **Fully Customizable:**
    * **Drag & Drop:** Arrange cards exactly how you want them.
    * **Resize:** Change card sizes (**Tiny**, **Small**, **Medium**, **Large**) or resize individually.
    * **Theming:** Customize every color to match your setup.
* **Smart Interactions:** Click on cards to toggle between units (e.g., **RAM %** vs. **GB**, **GPU Load** vs. **VRAM**).
* **Lightweight:** Runs in the background (**System Tray**) with minimal resource footprint.
* **Multilingual:** Switch between **English** and **German**.

---

## 📥 How to Use

1.  Download the latest `Sidepanel_v0.9.0.zip` from the **[Releases](../../releases)** page.
2.  Extract the ZIP file.
3.  Run `Sidepanel.exe` as **Administrator** (required to read hardware sensors).
4.  Right-click the **Tray Icon** (chip symbol near the clock) and select **"Open Dashboard"** or scan the IP displayed in the console/tooltip on your tablet.

---

## 🛠️ Development / Building from Source

If you want to modify the code or build it yourself, follow these steps.

### Requirements
* **Python 3.12+**
* **Windows** (due to hardware dependency)

### Setup

1.  Clone the repository:
    ```bash
    git clone [https://github.com/YOUR_USERNAME/Sidepanel.git](https://github.com/YOUR_USERNAME/Sidepanel.git)
    cd Sidepanel
    ```

2.  Install dependencies:
    ```bash
    pip install flask psutil pillow pystray pythonnet
    ```
    *(Note: You also need `pyinstaller` if you want to build the exe)*

3.  Run the application:
    ```bash
    python app.py
    ```

### Building the Executable

To create a standalone `.exe` file, use the following command:

```bash
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --icon="puls_chip.ico" --add-data "puls_chip.ico;." --add-data "LibreHardwareMonitorLib.dll;." --add-data "templates;templates" --add-data "LICENSE-3RD-PARTY.txt;." --name "Sidepanel" app.py
