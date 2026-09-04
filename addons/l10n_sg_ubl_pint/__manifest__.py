# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Singapore - UBL PINT',
    'countries': ['sg'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
    The UBL PINT e-invoicing format for Singapore is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['l10n_sg'],
    'auto_install': ['l10n_sg'],
    'author': 'Odoo S.A.',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
