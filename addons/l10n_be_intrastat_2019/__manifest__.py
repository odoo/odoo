# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Intrastat Declaration - Complement for 2019',
    'category': 'Accounting',
    'description': """
Adds the possibility to specify the origin country of goods and the partner VAT in the Intrastat XML report.
    """,
    'depends': ['l10n_be_intrastat'],
    'data': [
        'views/account_invoice_line_view.xml',
    ],
    'auto_install': True,
}
