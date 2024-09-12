{
    'name': 'Three countries fiscal positions',
    'version': '1.1',
    'category': 'Accounting/Accounting',
    'depends': ['base', 'account', 'base_vat'],
    'description': """
Module to allow the creation of fiscal positions between three countries.
Company country, Fiscal country and Delivery country.
===============================================

This module allows specific cases to be handled with a single fiscal position.
Said cases are the ones in which the company country is different than the one
the goods are expedited from which means that the VAT number and the tax used
for the mapping should not be the taxes of the company country.
    """,
    'data': [
        'views/partner_view.xml',
    ],
    'installable': True,
    'post_init_hook': '_post_init_hook',
    'license': 'LGPL-3',
}
