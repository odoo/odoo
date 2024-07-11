# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Malaysia - UBL PINT',
    'countries': ['my'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    'description': """
    The UBL PINT e-invoicing format for Malaysia is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['account_edi_ubl_cii'],
    'data': [
        'views/report_invoice.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'license': 'LGPL-3'
}
