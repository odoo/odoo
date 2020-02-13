# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Define Taxes as Python Code",
    'summary': """
        Allows to use python code to define taxes""",
    'description': """
        A tax defined as python code consists in two snippets of python code which are executed in a local environment containing data such as the unit price, product or partner.

        "Applicable Code" defines if the tax is to be applied.

        "Python Code" defines the amount of the tax.
        """,
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'views/account_tax_views.xml',
    ],
    'uninstall_hook': "uninstall_hook",
}
