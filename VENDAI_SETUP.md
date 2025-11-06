# VendAI Finance - Installation Complete! ✅

## Module Location
```
C:\Users\lided\projects\odoo\addons\vendai_finance\
```

---

## Quick Start (3 Options)

### Option 1: Auto-Install Script (Recommended)
```powershell
cd C:\Users\lided\projects\odoo
.\start_vendai.ps1
```

This script will:
- ✓ Check Odoo installation
- ✓ Verify module exists
- ✓ Activate Python venv
- ✓ Start Odoo with vendai_finance
- ✓ Auto-install the module

---

### Option 2: Manual Start (Full Control)
```powershell
cd C:\Users\lided\projects\odoo

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start Odoo with the module
python odoo-bin -d vendai_demo --addons-path=addons -i vendai_finance
```

---

### Option 3: Start Without Auto-Install
```powershell
cd C:\Users\lided\projects\odoo
.\venv\Scripts\Activate.ps1
python odoo-bin -d vendai_demo --addons-path=addons
```

Then manually install from UI:
1. Open http://localhost:8069
2. Create/select database
3. Go to **Apps** → **Update Apps List**
4. Remove "Apps" filter
5. Search "VendAI"
6. Click **Install**

---

## First Time Setup

### 1. Create Database (if needed)
When you first access http://localhost:8069, you'll see database manager:
- Master Password: `admin` (default)
- Database Name: `vendai_demo`
- Email: your email
- Password: your password
- Language: English
- Country: Kenya
- Demo data: ☐ (unchecked)

### 2. Install Required Dependencies
The module automatically installs with:
- ✓ base (Odoo core)
- ✓ purchase (Purchase module)
- ✓ account (Accounting)
- ✓ contacts (Contacts/Partners)

### 3. Verify Installation
After install, you should see:
- **VendAI Finance** menu in top bar
- Purchase Orders have "Offer Financing" button
- Partners have "VendAI Finance" tab

---

## Quick Test (5 minutes)

### Step 1: Create Lender
```
Contacts → Create
Name: Pezesha Limited
☑ Is a Vendor
VendAI Finance tab → ☑ Is Lender
Save
```

### Step 2: Create Supplier with History
```
Contacts → Create
Name: Kevian Kenya Ltd
☑ Is a Vendor
Save

# Create 3 Purchase Orders to build credit:
Purchase → Orders → Create
  Vendor: Kevian Kenya Ltd
  Add product line:
    Description: Beverages
    Quantity: 1000
    Unit Price: 500
  Total: KES 500,000
  
Confirm → Receive Products → Create Bill → Register Payment

Repeat 2 more times with different amounts
```

### Step 3: Check Credit Score
```
Contacts → Kevian Kenya Ltd → VendAI Finance tab
Expected Credit Score: 60-75 (based on 3 POs)
```

### Step 4: Offer Financing
```
Purchase → Orders → Create
  Vendor: Kevian Kenya Ltd
  Product: Mixed Beverages
  Total: KES 5,000,000
  
Click "Supplier Financing" tab
  → See credit score and eligibility
  
Click "Offer Financing" button
  → Set amount: KES 2,000,000
  → Interest: 4.5%
  → Tenor: 60 days
  → ☑ Buyer Guarantee
  → Click "Offer Financing"
```

### Step 5: View Facility
```
VendAI Finance → Credit Facilities
→ See VCF00001 in Kanban view
→ Open and explore
```

---

## Troubleshooting

### Module Not Found
```powershell
# Verify module exists
Test-Path "C:\Users\lided\projects\odoo\addons\vendai_finance\__manifest__.py"
# Should return: True

# If False, re-copy:
Copy-Item -Path "C:\Users\lided\Downloads\vendai-pos\odoo_vendai_finance" -Destination "C:\Users\lided\projects\odoo\addons\vendai_finance" -Recurse -Force
```

### Python Not Found
```powershell
# Check if venv exists
Test-Path "C:\Users\lided\projects\odoo\venv"

# Activate it
cd C:\Users\lided\projects\odoo
.\venv\Scripts\Activate.ps1

# Verify Python
python --version
# Should show: Python 3.10+ or 3.11+
```

### Port Already in Use
```powershell
# Use different port
python odoo-bin -d vendai_demo --addons-path=addons --http-port=8070 -i vendai_finance

# Then access: http://localhost:8070
```

### Database Connection Error
```powershell
# Check PostgreSQL is running
Get-Service -Name postgresql*

# If not running, start it:
Start-Service postgresql-x64-15  # (or your version)
```

### Module Install Fails
```powershell
# Update module list in Odoo shell
python odoo-bin shell -d vendai_demo

# In Python shell:
env['ir.module.module'].update_list()
exit()

# Then try installing from UI again
```

---

## Development Mode

### Enable Debug Mode
Add to URL: `?debug=1`
Example: http://localhost:8069/web?debug=1

### Update Module After Changes
```powershell
# Stop Odoo (Ctrl+C)
# Make your code changes
# Restart with update flag:
python odoo-bin -d vendai_demo --addons-path=addons -u vendai_finance
```

### View Logs
Logs appear in terminal where Odoo is running
Look for lines with `vendai` to see module activity

---

## Next Steps

1. ✅ **Module Copied** - Done!
2. 🚀 **Start Odoo** - Run `.\start_vendai.ps1`
3. 🧪 **Test Features** - Follow Quick Test above
4. 📊 **Create Demo Data** - Naivas + Kevian scenario
5. 🔌 **Integrate API** - Connect to Pezesha
6. 🎨 **Customize** - Add branding/styling
7. 🏢 **Go Live** - Deploy to production

---

## Support Commands

```powershell
# List all modules
cd C:\Users\lided\projects\odoo
Get-ChildItem .\addons | Select-Object Name

# Check module is there
Get-ChildItem .\addons\vendai_finance

# Start fresh database
python odoo-bin -d vendai_fresh --addons-path=addons -i vendai_finance

# Open Odoo shell for testing
python odoo-bin shell -d vendai_demo

# In shell, test credit scoring:
partner = env['res.partner'].search([('name', '=', 'Kevian Kenya Ltd')])[0]
print(f"Credit Score: {partner.vendai_credit_score}")
```

---

**Ready to launch! 🚀**

Open terminal and run:
```powershell
cd C:\Users\lided\projects\odoo
.\start_vendai.ps1
```

Then visit: http://localhost:8069
