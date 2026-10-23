{
    'name': 'Croatia - B2C e-invoicing',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
B2C e-invoicing for Croatia
    """,
    'depends': [
        'l10n_hr_edi',
        'certificate',
    ],
    'auto_install': ['l10n_hr_edi'],
    'data': [
        'data/template_request.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
    ],
    'website': 'https://www.odoo.com/app/accounting',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
