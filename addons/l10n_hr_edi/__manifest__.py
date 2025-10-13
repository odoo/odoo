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
        'data/cron.xml',
        'data/l10n_hr.kpd.category.csv',
        'security/ir.model.access.csv',
        'data/l10n_hr_tax_category.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/l10n_hr_kpd_category_views.xml',
        'views/product_views.xml',
        'views/report_invoice_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizard/l10n_hr_edi_mojeracun_reject_wizard_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
    'post_init_hook': 'post_init',
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
