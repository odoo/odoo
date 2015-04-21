# -*- coding: utf-8 -*-

{
    'name': 'Assets Management',
    'version': '1.0',
    'depends': ['account_accountant'],
    'author': 'Odoo S.A.',
    'description': """
Assets management.
==========================================

This Module manages the assets owned by a company or an individual. It will keep 
track of depreciation's occurred on those assets. And it allows to create Move's 
of the depreciation lines.

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
