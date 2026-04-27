{
    'author': 'Odoo',
    'name': 'Guatemala - E-Invoicing',
    'icon': '/account/static/description/l10n.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
E-invoice implementation for Guatemala
    """,
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'depends': [
        'account_debit_note',
        'account_tax_python',
        'l10n_gt',
        'l10n_latam_base',
    ],
    'data': [
        'data/l10n_gt_edi.phrase.csv',
        'data/l10n_latam_identification_type_data.xml',
        'data/res_partner_data.xml',
        'data/templates.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/l10n_gt_edi_phrase_views.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/demo_gt.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'post_init_hook': '_l10n_gt_edi_post_init',
}
