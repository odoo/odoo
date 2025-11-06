import os
import sys
import time
import psutil
import subprocess
from pathlib import Path

def is_odoo_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'odoo-bin' in ' '.join(str(x) for x in proc.info['cmdline']):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def start_odoo():
    odoo_path = Path(__file__).resolve().parent.parent
    config_path = odoo_path / 'config' / 'odoo.conf'
    
    if not is_odoo_running():
        try:
            startupinfo = None
            if os.name == 'nt':  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.Popen([
                sys.executable,
                str(odoo_path / 'odoo-bin'),
                '-c', str(config_path),
                '-d', 'vendai_db',
                '--http-port=8069'
            ], startupinfo=startupinfo)
            
            # Wait for Odoo to start
            time.sleep(5)
        except Exception as e:
            print(f"Error starting Odoo: {e}")

def main():
    try:
        # Start Odoo if not running
        start_odoo()
        
        # Start desktop UI
        main_path = Path(__file__).resolve().parent / 'main.py'
        subprocess.run([sys.executable, str(main_path)], check=True)
    except Exception as e:
        print(f"Error launching application: {e}")

if __name__ == "__main__":
    main()
