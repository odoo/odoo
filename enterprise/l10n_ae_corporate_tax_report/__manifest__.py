{
    'name': 'United Arab Emirates - Corporate Tax Report',
    'version': '1.0',
    'icon': '/account/static/description/l10n.png',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
United Arab Emirates Corporate Tax Report
=======================================================
Adds the Corporate Tax Report which can be accessed by going to Accounting > Reporting > Corporate Tax Report
    """,
    'depends': ['l10n_ae', 'account_reports'],
    'installable': True,
    'auto_install': True,
    'data': [
        'data/corporate_tax_report.xml',
        'data/actions.xml',
        'data/menuitems.xml',
        'data/account.account.tag.csv',

        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ae_corporate_tax_report/static/src/*',
        ],
    },
    'license': "OEEL-1",
    'post_init_hook': '_post_init_hook_configure_corporate_tax_report_data',
}
