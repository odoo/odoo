# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Developed in collaboration with Enabling NZ
{
    'name': "EFT Batch Payment",
    'icon': '/account/static/description/l10n.png',
    'summary': """Export payments as EFT files""",
    'author': 'Odoo S.A., Enabling NZ',
    'description': """
EFT Batch Payment
=================
""",
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'depends': ['account_batch_payment', 'l10n_nz'],
    'data': [
        'data/eft_data.xml',
        'views/account_batch_payment_views.xml',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}
