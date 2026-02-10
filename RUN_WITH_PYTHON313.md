# Running Odoo with Python 3.13

Odoo 19 supports Python 3.13.

## How to Start Odoo

### Method 1: Using the Virtual Environment (Recommended)

```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
.\venv313\Scripts\Activate.ps1
python odoo-bin -c odoo.conf -d ninetydays
```

### Method 2: Direct Command

```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
C:\Users\rtorresjr\AppData\Local\Programs\Python\Python313\python.exe odoo-bin -c odoo.conf -d ninetydays
```

## Access Odoo

Once the server starts, open:
**http://localhost:8069**

## Login

- **Email/Username:** `admin`
- **Password:** `admin` (change this after first login!)

## Database

- **Database Name:** `ninetydays`
- **Database User:** `odoo`
- **PostgreSQL:** Running on localhost:5432

## Stop the Server

Press `Ctrl+C` in the terminal, or:
```powershell
Get-Process python | Where-Object {$_.CommandLine -like '*odoo*'} | Stop-Process
```

## Create New Database

If you want to create a new database:

1. Start Odoo without `-d` parameter:
   ```powershell
   .\venv313\Scripts\Activate.ps1
   python odoo-bin -c odoo.conf
   ```

2. Access http://localhost:8069
3. Use the Database Manager
4. Master Password: `odoo123`

## Why Python 3.13

- Avoids template rendering errors. Database manager works. Officially supported by Odoo 19.

## Virtual Environment Location

The virtual environment is in:
```
C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo\venv313\
```

To activate it:
```powershell
.\venv313\Scripts\Activate.ps1
```
