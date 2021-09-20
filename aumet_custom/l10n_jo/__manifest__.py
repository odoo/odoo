# -*- encoding: utf-8 -*-

{
    'name': 'Aumet Chart of Accounts ',
    'version': '14.0.0.0',
    'author': "aumet",
    'category': 'Localization',
    'description': """
     Arabic localization for most arabic countries.
    """,
    'depends': ['stock','account', 'l10n_multilang','product','point_of_sale','base','aumet_product_template_qr','product_expiry'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/l10n_ye_chart_data.xml',
        'data/account_chart_template_configure_data.xml',

    ],
     'images': ['static/description/banner.png'],
     'license': 'AGPL-3',
    'post_init_hook': 'load_translations',
}
