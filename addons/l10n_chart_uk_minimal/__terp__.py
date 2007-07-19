#
# This module provides a minimal UK chart of accounts for building upon further
# Tiny ERP's default currency and accounts are remapped to this chart
#
# This module works for TinyERP 4.1.0 (and, assumed, onwards). 
# This module does not work for TinyERP 4.0.2 and before.
#
# VAT is structured thus:
#  - the user company is assumed to be non-VAT exempt (easy to modify, however)
#  - categories OVATS (Standard), OVATR (Reduced), OVATZ (Zero) should be
#    assigned to the customer taxes section of products (depending on the product)
#  - categories IVATS (Standard), IVATR (Reduced), IVATZ (Zero) should be
#    assigned to the supplier taxes section of products (depending on the product)
#  - categories OVATX (eXempt), OVATO (Out of scope), or nothing at all should be
#    assigned to default tax field of customers (depending on the customer)
#  - customer categorization trumps product categorization (unchanged Tiny functionality)
#  - on purchases, upon invoicing
#    - the base amount (ex-VAT) appears in the appropriate input base category (S, R, Z)
#    - the VAT amount appears in the appropriate input VAT category (S, R)
#    - invoice lines can be traced in these VAT categories
#    - refunds of invoices are deducted from the input category
#  - on sales, upon invoicing
#    - the base amount (ex-VAT) appears in the appropriate output base category (S, R, Z, X, O)
#    - the VAT amount appears in the appropriate output VAT category (S, R)
#    - invoice lines can be traced in these VAT categories
#    - refunds of invoices are deducted from the output category
#
# This forms a basis for accrual tax accounting
# Cash tax accounting can be accommodated with further processing in TinyERP
#
# Status beta 0.92 - tested on TinyERP 4.1.0
# Status beta 0.93 - tested on TinyERP 4.1.0
# - trivial change to depend only on 'account' 
#   (seemed to be important for importing with no demo data)
# Status 1.0 - tested on TinyERP 4.1.0, 4.0.3
# - COGS account type fixed
#
{
	"name" : "United Kingdom - minimal",
	"version" : "1.0",
	"author" : "Seath Solutions Ltd",
	"website": "http://www.seathsolutions.com",
	"category" : "Localisation/Account charts",
	"depends" : ["base", "account", "base_iban", "base_vat", "account_chart"],
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["account_chart.xml","account_tax.xml"],
	"active": False,
	"installable": True
}
