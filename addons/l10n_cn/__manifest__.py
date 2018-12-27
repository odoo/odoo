# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2008-2008 凯源吕鑫 lvxin@gmail.com   <basic chart data>
#                         维智众源 oldrev@gmail.com  <states data>
# Copyright (C) 2012-2012 南京盈通 ccdos@intoerp.com <small business chart>
# Copyright (C) 2008-now  开阖软件 jeff@osbzr.com    < PM and LTS >
# Copyright (C) 2018-now  jeffery9@gmail.com

{
    'name': 'China - Accounting',
    'version': '1.8',
    'category': 'Localization',
    'author': 'www.openerp-china.org',
    'maintainer': 'jeff@osbzr.com',
    'website': 'http://openerp-china.org',
    'description': """
Includes the following data for the Chinese localization
========================================================

Account Type/科目类型

State Data/省份数据

    """,
    'depends': ['base', 'account', 'l10n_multilang'],
    'data': [
        'data/res_country_state_data.xml',
        'data/account_account_type_data.xml',
        'data/account_tax_group_data.xml',
    ],
}
