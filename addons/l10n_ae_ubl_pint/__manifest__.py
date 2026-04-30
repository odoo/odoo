# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'UAE - UBL PINT',
    'countries': ['ae'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
    The UBL PINT e-invoicing format for UAE is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['account_edi_ubl_cii', 'l10n_ae'],
    'author': 'Odoo S.A.',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
