# VendAI Supplier Finance Module for Odoo

## Overview
This module enables **tripartite supplier financing** within Odoo's Purchase Order workflow. It allows buyers to offer financing to suppliers, with repayment automatically guaranteed and deducted from invoice payments.

## Features
- **Buyer-Backed Financing**: Buyers offer working capital to suppliers directly on Purchase Orders
- **Automatic Credit Scoring**: Real-time credit scores (0-100) based on transaction history
- **Tripartite Model**: Buyer guarantees repayment, removing default risk for lenders
- **Seamless Integration**: Financing embedded in PO workflow, no separate apps needed
- **Auto-Repayment**: Invoice payments automatically split between lender and supplier
- **API Ready**: Integration hooks for Pezesha, Kuunda, and other lenders

## Installation

### Requirements
- Odoo 17.0 or later
- Python 3.10+
- Modules: base, purchase, account, contacts

### Steps
1. Copy `odoo_vendai_finance` folder to your Odoo addons path
2. Restart Odoo server
3. Update Apps List (Settings > Apps > Update Apps List)
4. Search for "VendAI Supplier Finance"
5. Click Install

## Usage

### As a Buyer (e.g., Naivas)
1. Create a Purchase Order for a supplier
2. If supplier has good credit score (>50), "Offer Financing" button appears
3. Click button, set financing amount (up to 60% of PO value)
4. Confirm guarantee: "I will deduct repayment from invoice payment"
5. Supplier receives notification with offer

### As a Supplier (e.g., Kevian Kenya Ltd)
1. Open Purchase Order with financing offer
2. View terms: Principal, Interest Rate, Tenor
3. Click "Accept Financing"
4. Enter bank account details
5. Funds disbursed within 24 hours

### As a Lender (e.g., Pezesha)
1. Integration via API (docs coming soon)
2. Receive credit applications with buyer guarantee
3. Auto-approve based on buyer creditworthiness
4. Disburse funds via bank transfer
5. Receive repayment automatically when invoice paid

## Credit Scoring Algorithm
- **Transaction Volume** (30 points): > KES 50M = 30 pts
- **Transaction Count** (20 points): > 50 POs = 20 pts
- **On-Time Payment Rate** (40 points): 100% on-time = 40 pts
- **Recency** (10 points): PO within 30 days = 10 pts
- **Maximum Score**: 100

## Configuration

### Set up Lenders
1. Go to Contacts
2. Create partner (e.g., "Pezesha")
3. Check "Is Lender" field
4. Configure API URL (optional)

### Set Interest Rates
Default: 4.5% for 60 days (~27% annualized)
Can be customized per-offer in wizard

### Set Minimum Thresholds
- Minimum Credit Score: 50
- Minimum PO Amount: KES 100,000
- Minimum Financing: KES 100,000

## API Integration (Coming Soon)
- Pezesha Patascore API
- Kuunda Hapa Cash/Kazi Cash
- Custom lender webhook endpoints

## Demo Data
Includes:
- Naivas (Buyer)
- Kevian Kenya Ltd (Supplier with 82/100 score)
- 6 months transaction history
- Sample financing offer

## Support
- Email: support@vendai.co
- Website: https://vendai.co
- GitHub: https://github.com/timothylidede/vendai-pos

## License
LGPL-3

## Version
1.0.0 (November 2025)
