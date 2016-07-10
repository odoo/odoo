# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2008-2008 凯源吕鑫 lvxin@gmail.com   <basic chart data>
#                         维智众源 oldrev@gmail.com  <states data>
# Copyright (C) 2012-2012 南京盈通 ccdos@intoerp.com <small business chart>
# Copyright (C) 2008-now  开阖软件 jeff@osbzr.com    < PM and LTS >

{
    'name': '中国本地化基础数据',
    'version': '1.8',
    'category': 'Localization/Account Charts',
    'author': 'www.openerp-china.org',
    'maintainer': 'jeff@osbzr.com',
    'website': 'http://openerp-china.org',
    'description': """
此模块包含基础模块的本地化数据
==============================
1, 中国省份数据
2, 科目类型



    """,
    'depends': ['base', 'account'],
    'data': [
        'base_data.xml',
        'account_chart_type.xml',
    ],
    'license': 'GPL-3',
    'installable': True,
}
