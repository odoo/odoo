# -*- coding: utf-8 -*-
{
    'name': "Define Taxes as Python Code",
    'summary': """
        Allows to use python code to define taxes""",
    'description': """
        A tax defined as python code consists in two snippets of python code which are executed in a local environment containing data such as the unit price, product or partner.

        "Applicable Code" defines if the tax is to be applied.

        "Python Code" defines the amount of the tax.
        """,
    'author': "Odoo SA",
    'category': 'Accounting &amp; Finance',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'account_tax_python.xml',
    ],
}
