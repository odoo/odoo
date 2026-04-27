{
    'name': 'UK - Construction Industry Scheme',
    'countries': ['gb'],
    'author': 'Odoo',
    'version': '1.0',
    'category': 'Accounting/Localizations/UK/CIS',
    'description': """
Construction Industry Scheme for United Kingdom
================================================
    """,
    'depends': [
        'l10n_uk_reports',
        'l10n_uk_hmrc',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cis_report.xml',
        'data/ir_cron.xml',
        'data/mail_template_data.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/template_cis_monthly_return_body.xml',
        'wizard/monthly_return_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_uk_reports_cis/static/src/components/**/*',
        ],
    },
    'license': 'OEEL-1',
    'installable': True,
    'post_init_hook': '_l10n_uk_reports_cis_post_init',
}
