# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Malaysia - UBL PINT',
    'countries': ['my'],
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    'description': """
    The UBL PINT e-invoicing format for Malaysia is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['account_edi_ubl_cii'],
    'author': 'Odoo S.A.',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
