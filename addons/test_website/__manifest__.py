# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Test',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9876,
    'summary': 'Website Test, mainly for module install/uninstall tests',
    'description': """This module contains tests related to website. Those are
present in a separate module as we are testing module install/uninstall/upgrade
and we don't want to reload the website module every time, including it's possible
dependencies. Neither we want to add in website module some routes, views and
models which only purpose is to run tests.""",
    'depends': [
        'website',
    ],
    'data': [
        'views/templates.xml',
        'data/test_website_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
