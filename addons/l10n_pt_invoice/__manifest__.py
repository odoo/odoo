# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Invoice',
    'version': '1.0.0',
    'author': 'Odoo S.A.',
    'category': 'Accounting/Localizations',
    'license': 'LGPL-3',
    'description': """
    Invoices for the Portuguese Republic
""",
    'depends': ['l10n_pt', 'account'],
    'data': [
        'views/report_invoice.xml',
    ],
}
