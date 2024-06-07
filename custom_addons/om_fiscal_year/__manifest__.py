# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo 17 Fiscal Year & Lock Date',
    'version': '17.0.1.2',
    'category': 'Accounting',
    'summary': 'Odoo 17 Fiscal Year, Fiscal Year in Odoo 17, Lock Date in Odoo 17',
    'description': 'Odoo 17 Fiscal Year, Fiscal Year in Odoo 17',
    'live_test_url': 'https://www.youtube.com/watch?v=Kj4hR7_uNs4',
    'sequence': '1',
    'website': 'https://www.odoomates.tech',
    'author': 'Odoo Mates, Odoo SA',
    'maintainer': 'Odoo Mates',
    'license': 'LGPL-3',
    'support': 'odoomates@gmail.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'security/account_security.xml',
        'wizard/change_lock_date.xml',
        'views/fiscal_year.xml',
        'views/settings.xml',
    ],
    'images': ['static/description/banner.png'],
}
