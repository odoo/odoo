# -*- coding: utf-8 -*-

{
    'name': 'Indian - Accounting Voucher',
    'version': '1.0',
    'author': 'OpenERP SA',
    'category': 'Localization/eInvoicing & Payments',
    'description': """
Voucher Report and Template
===========================

This module allows you following feature:
-----------------------------------------
    * make history for future when user change fields Amount of Payment, Partner, Write Off, Period, Journal.
    * Add new followers on voucher from all the invoice's followers attached in Account Vourcher lines
    * Add email template to be used by Finance Department to send receipt to customer once they receive Payment
    * Improve header of current voucher report such that it can display company details after title of report
""",
    'summary': 'Voucher Report, Template and Invoice Followers',
    'website': 'https://www.odoo.com',
    'data': [
        'voucher_report.xml',
        'views/report_voucher.xml',
        'account_voucher_action_data.xml',
        ],
    'depends': ['account_voucher'],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
