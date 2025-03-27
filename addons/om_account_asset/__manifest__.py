# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo 16 Assets Management',
    'version': '16.0.1.3.0',
    'author': 'Odoo Mates, Odoo SA',
    'depends': ['account'],
    'description': """Manage assets owned by a company or a person. 
        Keeps track of depreciation's, and creates corresponding journal entries""",
    'summary': 'Odoo 16 Assets Management',
    'category': 'Accounting',
    'sequence': 10,
    'website': 'https://www.odoomates.tech',
    'license': 'LGPL-3',
    'images': ['static/description/assets.gif'],
    'data': [
        'data/account_asset_data.xml',
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/asset_depreciation_confirmation_wizard_views.xml',
        'wizard/asset_modify_views.xml',
        'views/account_asset_views.xml',
        'views/account_move_views.xml',
        'views/account_asset_templates.xml',
        'views/asset_category_views.xml',
        'views/product_views.xml',
        'report/account_asset_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'om_account_asset/static/src/scss/account_asset.scss',
            'om_account_asset/static/src/js/account_asset.js',
        ],
        'web.qunit_suite_tests': [
            ('after', 'web/static/tests/legacy/views/kanban_tests.js', '/om_account_asset/static/tests/account_asset_tests.js'),
        ],
    },
}
