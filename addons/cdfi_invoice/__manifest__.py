# -*- coding: utf-8 -*-
##############################################################################
#                 @author IT Admin
#
##############################################################################

{
    'name': 'Ventas Factura Electronica Mexico CFDI',
    'version': '12.12',
    'description': ''' Factura Electronica módulo de ventas para Mexico (CFDI 3.3)
    ''',
    'category': 'Accounting',
    'author': 'IT Admin',
    'website': 'www.itadmin.com.mx',
    'depends': [
        'base',
        'sale','account','purchase'
    ],
    'data': [
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/product_view.xml',
        'views/account_invoice_view.xml',
        'views/invoice_supplier_view.xml',
        'views/account_payment_view.xml',
        'views/account_tax_view.xml',
        'views/sale_view.xml',
        'views/account_payment_term_view.xml',
        'views/purchase_view.xml',
        'views/account_journal_view.xml',
        'wizard/import_account_payment_view.xml',
        'report/invoice_report.xml',
        'report/payment_report.xml',
        'report/sale_report_templates.xml',
        'data/mail_template_data.xml',
        'data/cron.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'application': False,
    'installable': True,
    'price': 0.00,
    'currency': 'USD',
    'license': 'OPL-1',	
}
