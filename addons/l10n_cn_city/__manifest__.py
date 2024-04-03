# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2018-now  jeffery9@gmail.com

{
    'name': 'China - City Data',
    'version': '1.8',
    'icon': '/l10n_cn/static/description/icon.png',
    'category': 'Accounting/Localizations',
    'author': 'Jeffery Chen Fan<jeffery9@gmail.com>',
    'description': """
Includes the following data for the Chinese localization
========================================================

City Data/城市数据

    """,
    'depends': ['l10n_cn', 'base_address_extended'],
    'data': [
        'data/res_city_data.xml',
        'data/res_country_data.xml',
    ],
    'license': 'LGPL-3',
}
