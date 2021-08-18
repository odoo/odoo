# -*- encoding: utf-8 -*-

{
    'name': 'Jordan Chart of Accounts standard',
    'version': '13.0.0.0',
    'author': "Mali, MuhlhelITS",
    'website': "http://natigroup.biz",
    'category': 'Localization',
    'description': """
     Arabic localization for most arabic countries.
    """,
    'depends': ['account', 'l10n_multilang'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.group.csv',
        'data/account.account.template.csv',
        'data/l10n_ye_chart_data.xml',
        'data/account_chart_template_configure_data.xml',
    ],
     'images': ['static/description/banner.png'],
     'license': 'AGPL-3',
    'post_init_hook': 'load_translations',
}
