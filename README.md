# Sidepanel

**A lightweight, customizable hardware monitor dashboard designed for second screens.**



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
4.  Right-click the **Tray Icon** (chip symbol near the clock) and select **"Open Dashboard"** or enter 192.168.178.36:5000 in the Browser of your Device.

---

⚙️ Configuration
Settings are saved automatically in config.json. You can enable Expert Mode for color customization by setting "show_advanced_colors": true in this file manually, or simply use the settings gear in the UI.

---

❤️ Acknowledgments & Special Thanks

A huge thank you goes to the creators and contributors of LibreHardwareMonitor.

This project relies on the LibreHardwareMonitorLib.dll to access low-level hardware sensors (temperatures, clock speeds, etc.). Without their incredible open-source work and this library, Sidepanel would not be possible.

Please check out their repository if you are interested in how hardware monitoring works under the hood!

---

⚖️ License
Sidepanel itself is open source. Feel free to fork and improve!

This project includes the LibreHardwareMonitorLib.dll library, which is licensed under the Mozilla Public License 2.0 (MPL 2.0). The source code for the library is available at the link above. No changes were made to the library file itself. See license.txt for the full license text.
