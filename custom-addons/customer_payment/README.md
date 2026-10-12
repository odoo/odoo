# Customer Payment Tracking

## Overview
This module allows you to track customer payments and view their invoice history from Point of Sale.

## Features
- **Customer Payment Records**: Create payment records for customers by year
- **Automatic Invoice Loading**: Process button automatically loads all invoices for a customer in the specified year
- **Payment Entry Tracking**: Record multiple payment entries with dates, amounts, and notes
- **Balance Calculation**: Compare total invoices vs total payments to see outstanding balance
- **Audit Trail**: Track changes to customer, year, and status fields

## Usage

### Creating a Payment Record
1. Navigate to **Customer Payments** menu
2. Click **Create**
3. Select a **Customer** and **Year**
4. Click **Process** button to load all invoices for that customer/year
5. Add payment entries in the **Payment Entries** tab with:
   - Receiving Date
   - Amount
   - Note (optional)
6. View the **Summary** tab to see:
   - Total Invoice Amount
   - Total Payment Amount
   - Balance (Outstanding amount)

### Workflow
1. POS creates invoices for customers
2. Create a new Customer Payment record when customer comes to pay
3. Process the record to load all invoices for the year
4. Add payment entries as customer makes payments
5. Track balance to see how much customer still owes

## Models

### customer.payment
Main model for tracking customer payments.

**Key Fields:**
- `partner_id`: Customer
- `year`: Year for invoice filtering
- `state`: Draft or Processed
- `invoice_ids`: Many2many relation to invoices
- `payment_entry_ids`: One2many relation to payment entries
- `total_invoice_amount`: Computed total of all invoices
- `total_payment_amount`: Computed total of all payment entries
- `balance`: Total invoices - Total payments

### payment.entry
Payment entry lines for recording individual payments.

**Key Fields:**
- `payment_date`: Date payment was received
- `amount`: Payment amount
- `note`: Optional note

## Dependencies
- point_of_sale
- account
- mail

## Installation
1. Copy the module to your Odoo addons directory
2. Update the app list
3. Install the "Customer Payment Tracking" module

## Security
- **POS Users**: Can read, write, and create payment records
- **POS Managers**: Full access including delete permissions

## Author
Your Company

## License
LGPL-3
