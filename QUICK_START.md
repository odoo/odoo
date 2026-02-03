# Quick Start Guide - Odoo is Starting!

## 🚀 Server Status

Odoo server has been started! It may take 30-60 seconds to fully initialize, especially on the first run.

## 🌐 Access Odoo

**Open your browser and go to:**
```
http://localhost:8069
```

## 🔐 First Login

When you first access Odoo, you'll see either:
1. **Database Manager** - Create or select a database
2. **Login Screen** - If database is already initialized

**Default Credentials:**
- **Email/Username:** `admin`
- **Password:** `admin` ⚠️ **Change this immediately after first login!**

## 📋 What to Do Next

1. **Wait for the page to load** (may take 30-60 seconds on first start)
2. **If you see Database Manager:**
   - Database name: `mycompany` (or create a new one)
   - Master password: `admin`
   - Click "Create Database" or "Select Database"
3. **If you see Login Screen:**
   - Enter username: `admin`
   - Enter password: `admin`
4. **After logging in:**
   - Change the admin password immediately
   - Complete the setup wizard
   - Start configuring your Odoo instance!

## 🛑 Stop the Server

To stop Odoo server, run:
```powershell
Get-Process python | Where-Object {$_.CommandLine -like '*odoo*'} | Stop-Process
```

Or find the Python process running Odoo and end it from Task Manager.

## 🔄 Start Again Later

To start Odoo again:
```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
python odoo-bin -c odoo.conf -d mycompany
```

Or run it in the background:
```powershell
Start-Process python -ArgumentList "odoo-bin", "-c", "odoo.conf", "-d", "mycompany"
```

## ⚠️ Troubleshooting

### Page Won't Load
- Wait a bit longer (first start takes time)
- Check if Python process is running
- Check `odoo.log` for errors

### Database Error
- Verify PostgreSQL is running: `Get-Service postgresql-x64-16`
- Check `odoo.conf` has correct database settings

### Port Already in Use
- Change `http_port` in `odoo.conf` to another port (e.g., 8070)
- Or stop the process using port 8069

## ✅ Setup Complete!

Your Odoo installation is ready! Enjoy using Odoo! 🎉
