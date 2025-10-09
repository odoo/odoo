{
    'name': 'Croatia - e-invoicing',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
e-invoicing for Croatia
    """,
    'depends': [
        'l10n_hr',
        'account_edi_ubl_cii',
        'account_peppol',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_hr_vat_expence_category.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/ubl_hr_templates.xml',
        'wizard/eracun_registration_views.xml',
    ],
    'installable': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
