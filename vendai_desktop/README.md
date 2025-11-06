VendAI Desktop (Windows)

Quick start (PowerShell):

1. Install Python dependencies (once):

   python -m pip install -r requirements.txt

2. Launch the desktop app (starts Odoo and the app):

   .\run_desktop.ps1

If you'd rather run manually:

- Start Odoo: python ..\odoo-bin -c ..\config\odoo.conf -d vendai_db --http-port=8069
- Start app: python app.py

Notes:
- The PowerShell launcher starts Odoo hidden and waits up to 60s for an HTTP response.
- On first run you may need to create or upgrade the `vendai_db` database using Odoo's standard commands.
- If you prefer a single-file executable, we can create a PyInstaller bundle next.
