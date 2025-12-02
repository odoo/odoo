# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Malaysia - E-invoicing',
    'countries': ['my'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    "summary": "E-invoicing using MyInvois",
    'description': """
    This modules allows the user to send their invoices to the MyInvois system.
    """,
    # The export does not depend on the pint format, but we need to reuse the fields defined there.
    'depends': ['l10n_my', 'l10n_my_ubl_pint', 'account_edi_proxy_client'],
    'data': [
        'data/ir_cron.xml',
        'data/l10n_my_edi.industry_classification.csv',

        'security/ir.model.access.csv',
        'security/myinvois_security.xml',

        'views/account_move_view.xml',
        'views/account_tax_view.xml',
        'views/l10n_my_edi_industrial_classification_views.xml',
        "views/myinvois_document_views.xml",
        'views/product_template_view.xml',
        'views/report_invoice.xml',
        'views/res_company_view.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_view.xml',
        'views/account_portal_templates.xml',

        'wizard/myinvois_consolidate_invoice_wizard.xml',
        'wizard/myinvois_document_status_update_wizard.xml',
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3'
}
