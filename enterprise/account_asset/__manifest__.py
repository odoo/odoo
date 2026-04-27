# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Assets Management',
    'description': """
Assets management
=================
Manage assets owned by a company or a person.
Keeps track of depreciations, and creates corresponding journal entries.

    """,
    'category': 'Accounting/Accounting',
    'sequence': 32,
    'depends': ['account_reports'],
    'data': [
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/asset_modify_views.xml',
        'views/account_account_views.xml',
        'views/account_asset_views.xml',
        'views/account_asset_group_views.xml',
        'views/account_move_views.xml',
        'data/assets_report.xml',
        'data/account_report_actions.xml',
        'data/menuitems.xml',
    ],
    'demo': [
        'demo/account_asset_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'account_reports.assets_financial_report': [
            'account_asset/static/src/scss/account_asset.scss',
        ],
        'web.assets_backend': [
            'account_asset/static/src/scss/account_asset.scss',
            'account_asset/static/src/components/**/*',
            'account_asset/static/src/views/**/*',
            'account_asset/static/src/web/**/*',
        ],
        'web.assets_web_dark': [
            'account_asset/static/src/scss/*.dark.scss',
        ],
    }
}
