# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "France - Adding Mandatory Invoice Mentions (Decree no. 2022-1299)",
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'description': """
Add new address fields necessary to respect the new 2024-07-01 French law
(https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000046383394) to invoices.
""",
    'depends': [
        'l10n_fr',
    ],
    'auto_install': True,
    'data': [
        'views/report_invoice.xml',
    ],
    'license': 'LGPL-3',
}
