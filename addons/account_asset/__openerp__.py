# -*- coding: utf-8 -*-

{
    'name': 'Assets & Revenue Recognitions Management',
    'version': '1.0',
    'depends': ['account_accountant'],
    'author': 'Odoo S.A.',
    'description': """
Assets management.
==========================================

It allows you to manage the assets owned by a company or a person.
It keeps track of the depreciation occurred on those assets, and creates account moves for those depreciation lines.

Revenue recognitions.
===========================================
It allows you to manage the revenue recognition on product's sale.
It keeps track of the installments occurred on those revenue recognition, and creates account moves for those installment lines.

    """,
    'website': 'https://www.odoo.com/page/accounting',
    'category': 'Accounting & Finance',
    'sequence': 32,
    'demo': ['account_asset_demo.xml'],
    'data': [
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/account_asset_change_duration_view.xml',
        'wizard/wizard_asset_compute_view.xml',
        'views/account_asset_view.xml',
        'views/account_asset_invoice_view.xml',
        'report/account_asset_report_view.xml',
        'views/account_asset.xml',
    ],
    'qweb': [
        "static/src/xml/account_asset_template.xml",
    ],
    'installable': True,
    'application': False,
}
