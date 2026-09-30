# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Singapore - UBL PINT',
    'countries': ['sg'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
    The UBL PINT e-invoicing format for Singapore is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['account_edi_ubl_cii'],
    'installable': True,
    'author': 'Odoo S.A.',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
