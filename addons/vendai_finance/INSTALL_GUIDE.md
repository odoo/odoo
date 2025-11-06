# Quick Install Guide - VendAI Odoo Module

## ✅ Module Status: 100% COMPLETE

All files created and ready for installation!

---

## 📦 What's Included

```
odoo_vendai_finance/
├── 13 Python files (2,000+ lines)
├── 6 XML view files (42,689 bytes)
├── 3 Documentation files
├── Security & data files
└── Empty static assets folders (optional)
```

---

## 🚀 3-Minute Installation

### Option 1: Local Odoo Installation

**Step 1: Install Odoo 17**
```powershell
# Download Odoo 17 Community Edition
# https://www.odoo.com/page/download

# Or use Docker:
docker run -d -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres --name odoo-db postgres:15
docker run -p 8069:8069 --name odoo --link odoo-db:db -t odoo:17.0
```

**Step 2: Copy Module**
```powershell
# Find your Odoo addons directory, usually:
# C:\Program Files\Odoo 17.0\server\odoo\addons
# or
# C:\odoo\addons

# Copy the module:
Copy-Item -Recurse "C:\Users\lided\Downloads\vendai-pos\odoo_vendai_finance" "C:\odoo\addons\"
```

**Step 3: Restart Odoo**
```powershell
# Windows Service:
Restart-Service odoo-server

# Or command line:
cd C:\odoo
.\python.exe odoo-bin -d vendai_demo -i vendai_finance
```

**Step 4: Activate in Odoo**
1. Open browser: http://localhost:8069
2. Create new database or login
3. Go to **Apps** menu
4. Click **Update Apps List**
5. Remove "Apps" filter
6. Search "VendAI"
7. Click **Install**

---

### Option 2: Odoo.sh (Cloud)

**Step 1: Create Odoo.sh Project**
1. Go to https://www.odoo.sh
2. Create new project (17.0)

**Step 2: Push Module via Git**
```bash
git init
git add .
git commit -m "Add VendAI Finance module"
git remote add odoo <your-odoo-sh-git-url>
git push odoo master
```

**Step 3: Install from Odoo.sh**
1. Go to your Odoo.sh instance
2. **Apps** → **Update Apps List**
3. Install **VendAI Supplier Finance**

---

## 🧪 Quick Test

### Create Demo Scenario (5 minutes)

**1. Create Lender Partner**
```
Name: Pezesha Limited
Is a Vendor: ✓
VendAI Finance tab → Is Lender: ✓
```

**2. Create Supplier (Kevian)**
```
Name: Kevian Kenya Ltd
Is a Vendor: ✓
```

**3. Create 3 Historical POs** (to build credit score)
```
PO #1:
  Vendor: Kevian Kenya Ltd
  Product: Bottled Water
  Quantity: 1000
  Unit Price: 500
  Total: KES 500,000
  → Confirm → Receive → Create Bill → Register Payment

PO #2:
  Vendor: Kevian Kenya Ltd
  Product: Soft Drinks
  Quantity: 2000
  Unit Price: 600
  Total: KES 1,200,000
  → Confirm → Receive → Create Bill → Register Payment

PO #3:
  Vendor: Kevian Kenya Ltd
  Product: Juices
  Quantity: 1500
  Unit Price: 700
  Total: KES 1,050,000
  → Confirm → Receive → Create Bill → Register Payment
```

**4. Check Credit Score**
```
Contacts → Kevian Kenya Ltd → VendAI Finance tab
Expected: Credit Score = 65-75
```

**5. Create New PO with Financing**
```
Purchase → Orders → Create
  Vendor: Kevian Kenya Ltd
  Product: Mixed Beverages
  Total: KES 5,000,000
  
Click "Supplier Financing" tab
  → Should show "Eligible for Financing"
  → Credit Score visible
  
Click "Offer Financing" button
  → Wizard opens
  → Max Financing: ~KES 2,250,000 (45%)
  → Set Financing: KES 2,000,000
  → Interest: 4.5%
  → Tenor: 60 days
  → Check "Buyer Guarantee"
  → Click "Offer Financing"
```

**6. View Credit Facility**
```
VendAI Finance → Credit Facilities
  → Should see VCF00001 in "Offered" state
  → Open form
  → See all parties, amounts, terms
```

**7. Accept Financing (Supplier Side)**
```
VendAI Finance → Credit Facilities → VCF00001
  → Click "Accept Offer"
  → Enter bank details:
      Account: 1234567890
      Bank: Equity Bank Kenya
      Holder: Kevian Kenya Ltd
  → Check "Accept Terms"
  → Click "Accept Offer"
  
  → Facility auto-submits to lender (mock)
  → State changes: Offered → Accepted → Approved → Disbursed
```

**Success!** You've completed a full financing cycle.

---

## 🎯 What You'll See

### Menu Items
- **VendAI Finance** (top menu)
  - Credit Facilities
  - Suppliers
  - Lenders
  - Reports → Credit Scores
  - Configuration → Settings

### Purchase Order Enhancements
- **Offer Financing** button (when eligible)
- **Credit Facility** smart button
- **Supplier Financing** tab with:
  - Credit score progress bar
  - Eligibility status
  - Financing terms

### Partner (Supplier) Enhancements
- **Credit Facilities** smart button
- **Active Facilities** smart button
- **VendAI Finance** tab with:
  - Credit score (0-100)
  - Score breakdown
  - Facility statistics

### Credit Facility Management
- **Kanban Board** (by state)
- **List View** (with color coding)
- **Form View** (full details)
- **Search/Filters** (by state, party, date)

---

## 🐛 Troubleshooting

### Module Not Appearing in Apps
```python
# Restart Odoo in update mode
./odoo-bin -d your_db -u all --stop-after-init
```

### Import Errors
Check dependencies are installed:
- base (core)
- purchase
- account
- contacts

### Views Not Loading
```python
# Update module
Apps → VendAI Supplier Finance → Upgrade
```

### Credit Score = 0
- Ensure supplier has completed Purchase Orders
- POs must be in "Purchase Order" or "Done" state
- Invoices must be marked as "Paid"
- Check invoice payment dates vs due dates

---

## 📞 Support

### Check Logs
```powershell
# Windows
Get-Content "C:\Program Files\Odoo 17.0\server\odoo.log" -Tail 50

# Linux
tail -f /var/log/odoo/odoo-server.log
```

### Debug Mode
Add to URL: `?debug=1`
Example: http://localhost:8069/web?debug=1

### Python Shell Testing
```python
# Start Odoo shell
./odoo-bin shell -d your_db

# Test credit scoring
partner = env['res.partner'].search([('name', '=', 'Kevian Kenya Ltd')])[0]
print(f"Credit Score: {partner.vendai_credit_score}")

# Test facility creation
facility = env['vendai.credit.facility'].create({
    'purchase_order_id': 1,
    'buyer_id': 1,
    'supplier_id': 2,
    'lender_id': 3,
    'po_amount': 5000000,
    'principal': 2000000,
    'interest_rate': 4.5,
    'tenor_days': 60,
})
print(f"Created: {facility.name}")
```

---

## 🎓 Resources

- **Odoo Documentation**: https://www.odoo.com/documentation/17.0/
- **Module README**: `odoo_vendai_finance/README.md`
- **Build Summary**: `odoo_vendai_finance/BUILD_SUMMARY.md`
- **This Guide**: `odoo_vendai_finance/VIEWS_COMPLETE.md`

---

## 🚀 Next Steps

1. ✅ **Install & Test** - Verify all features work
2. 📊 **Demo Data** - Create Naivas/Kevian scenario
3. 🔌 **API Integration** - Replace mock with Pezesha API
4. 🎨 **Branding** - Add logo and custom styling
5. 📱 **Mobile Test** - Verify responsive views
6. 🏢 **Partner Demo** - Show to Advance Insight
7. 🌍 **Production Deploy** - Launch with first client

---

**Ready to transform supplier financing in Kenya! 🇰🇪**
