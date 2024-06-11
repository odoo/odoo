# -*- coding: utf-8 -*-
{
    'name' : "Advance Payment for Sale and Purchase",
    "author": "Edge Technologies",
    'version': '15.0.1.1',
    'live_test_url': "https://youtu.be/0UpNsWX_jR4",
    "images":['static/description/main_screenshot.png'],
    'summary': 'App vendor Advance Payment for sale purchase Advance Payment sale Advance Payment customer advance payment Vendor Payment Adjustment Account Advance Payment vendor bill advance payment sale order advance payment purchase order advance payment for vendor',
    'description' : """ This app help to user, make advance payment and posted journal entries from sale order and purchase order, also maintain Advance Payment History in Sale and Purchase.4

Sale & Purchase Advance Payment
Customer Advance payment 
Odoo Advance Payment for purchase order
payment in Advance Payment sale Advance Payment purchase Advance Payment
so Advance Payment po Advance Payment
payment before
payment first
first payment 
advance payment on Sale Orders Advance Payment tab
Advance Payments 
Advance Payment Allocation
Supplier Advance Payments different payment 
Advance Payment Allocation expense advance and submit expense claim
Customer and Vendor Payment Adjustment
Account Advance Payment
Customer payment Advance
Supplier/Vendor Advance payment
Supplier Advance payment
Vendor Advance payment Supplier Advance Payments Management
Vendor Advance payment
advance payment on Purchase Orders
Payment of vendor/supplier on Purchase Order
advance payment
register advance payment for sales order
apply advance payment on invoice
make advance payment for invoices
add advance payment for vendor bills
make advance payment for customer invoice
customer advance payment link agaist invoice
reconcile advance payment agaist outstanding invoice
pay before purchase pay before sales

Sale Order Advance Payment
Advance Payment is necessary feature for any ERP System. 
Odoo Doesn't have feature to add Advance Payment of Invoice from Sales and Purchase. 
This app help to user to make advance payment from Sales Order and Purchase Order which creates posted journal entries from after the payment done.
This apps also maintain Advance Payment History in Sales and Purchase Order in Odoo accounting.
Advance payment history on sales order
advance payment history on purchase order


     """,
    "license" : "OPL-1",
    'depends' : ['sale_management','purchase','account'],
    'data': [
                'security/advance_payment_group.xml',
                'security/ir.model.access.csv',
                'views/res_config_view.xml',
                'views/sale_order_view.xml',
                'views/purchase_order_view.xml',
                'wizard/sale_advance_payment_wizard.xml',
                'wizard/purchase_advance_payment_wizard.xml',
             ],
    'installable': True,
    'auto_install': False,
    'price': 10,
    'currency': "EUR",
    'category': 'Accounting',
}
