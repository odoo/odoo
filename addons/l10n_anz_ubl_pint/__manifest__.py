# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Australia & New Zealand - UBL PINT',
    'countries': ['au', 'nz'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
    The UBL PINT e-invoicing format for Australia & New Zealand is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['account_edi_ubl_cii_tax_extension'],
    'installable': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
