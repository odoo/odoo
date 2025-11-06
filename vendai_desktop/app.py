import webview
import sys
import os
import subprocess
from pathlib import Path

def start_odoo():
    """Start Odoo server if not already running"""
    try:
        odoo_path = Path(__file__).resolve().parent.parent
        config_path = odoo_path / 'config' / 'odoo.conf'
        
        # Start Odoo in a separate process
        startupinfo = None
        if os.name == 'nt':  # Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    # Use a full, quoted command to avoid Windows path issues
    odoo_exec = str(odoo_path / 'odoo-bin')
    args = [odoo_exec, '-c', str(config_path), '-d', 'vendai_db', '--http-port=8069']
    subprocess.Popen([sys.executable] + args, startupinfo=startupinfo)
        
    except Exception as e:
        print(f"Error starting Odoo: {e}")

def main():
    # Start Odoo
    start_odoo()

    # Wait for Odoo HTTP endpoint to be available before opening the window
    import time
    import requests

    url = 'http://localhost:8069'
    timeout = 60
    start = time.time()
    print('Waiting for Odoo to become available at', url)
    while True:
        try:
            r = requests.get(url, timeout=2)
            # we don't require a 200; if we get any response the server is up
            print('Odoo HTTP responded:', r.status_code)
            break
        except Exception:
            if time.time() - start > timeout:
                print(f"Timeout waiting for Odoo at {url}.\nPlease start Odoo manually and then run this app.")
                return
            time.sleep(1)

    # Create window
    webview.create_window('VendAI - Smart POS', url, width=1280, height=800)
    webview.start()

if __name__ == '__main__':
    main()
