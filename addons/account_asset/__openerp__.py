# -*- coding: utf-8 -*-

{
    'name': 'Assets Management',
    'version': '1.0',
    'depends': ['account_accountant'],
    'description': """
Assets management
=================
Manage assets owned by a company or a person.
Keeps track of depreciations, and creates corresponding journal entries.

    """,
    'website': 'https://www.odoo.com/page/accounting',
    'category': 'Accounting',
    'sequence': 32,
    'demo': [
        'account_asset_demo.yml',
    ],
    # 'test': [
    #     '../account/test/account_minimal_test.xml',
    #     'test/account_asset_demo_test.xml',
    # ],
    'data': [
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/account_asset_change_duration_view.xml',
        'wizard/wizard_asset_compute_view.xml',
        'views/account_asset_view.xml',
        'views/account_asset_invoice_view.xml',
        'report/account_asset_report_view.xml',
        'views/account_asset.xml',
        'account_asset_cron.xml',
    ],
    'qweb': [
        "static/src/xml/account_asset_template.xml",
    ],
    'installable': True,
    'application': False,
}
