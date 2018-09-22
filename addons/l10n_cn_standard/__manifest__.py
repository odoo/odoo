# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2008-2008 凯源吕鑫 lvxin@gmail.com   <basic chart data>
#                         维智众源 oldrev@gmail.com  <states data>
# Copyright (C) 2012-2012 南京盈通 ccdos@intoerp.com <small business chart>
# Copyright (C) 2008-now  开阖软件 jeff@osbzr.com    < PM and LTS >
# Copyright (C) 2017-now  jeffery9@gmail.com

{
    'name': '会计科目表 - 中国企业会计准则',
    'version': '2.0',
    'category': 'Localization',
    'author': ['lvxin@gmail.co', 'oldrev@gmail.co', 'ccdos@intoerp.com', 'jeff@osbzr.com', 'jeffery9@gmail.com'],

    'website': 'http://shine-it.net',
    'description': """
Including the following data in the Accounting Standards for Business Enterprises
包含企业会计准则以下数据

* Chart of Accounts
* 科目表模板

* Account templates
* 科目模板

* Tax templates
* 税金模板

    """,
    'depends': ['l10n_cn'],
    'data': [
        'data/l10n_cn_standard_chart_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_templates.xml',
        'data/account_chart_template_data.xml',
        'data/account_chart_template_data.yml',
    ],
	'auto_install': True
}
