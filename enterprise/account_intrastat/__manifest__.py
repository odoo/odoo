# -*- coding: utf-8 -*-
{
    'name' : 'Intrastat Reports',
    'category': 'Accounting/Accounting',
    'version': '1.1',
    'description': """
Intrastat Reports
==================
    """,
    'depends': ['account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/country_data.xml',
        'data/code_transaction_data.xml',
        'data/code_transport_data.xml',
        # Commodity codes are loaded as CSV due to the huge amount of records.
        'data/account.intrastat.code.csv',
        'views/account_intrastat_code_view.xml',
        'views/product_view.xml',
        'views/res_country_view.xml',
        'views/res_config_settings_view.xml',
        'views/account_invoice_view.xml',
        'data/intrastat_report.xml',
        'data/intrastat_menus.xml',
        'views/report_invoice.xml',
        'views/account_move_view.xml',
    ],
    'demo': [
        'demo/product_demo.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_intrastat/static/src/components/**/*',
            'account_intrastat/static/src/scss/account_intrastat_report.scss',
        ],
    },
}
