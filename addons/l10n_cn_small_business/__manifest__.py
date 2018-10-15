# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2008-2008 凯源吕鑫 lvxin@gmail.com   <basic chart data>
#                         维智众源 oldrev@gmail.com  <states data>
# Copyright (C) 2012-2012 南京盈通 ccdos@intoerp.com <small business chart>
# Copyright (C) 2008-now  开阖软件 jeff@osbzr.com    < PM and LTS >
# Copyright (C) 2015-now  亘盈信息技术 jeffery9@gmail.com

{
    'name': 'China - Small Business CoA',
    'version': '1.8',
    'category': 'Localization',
    'author': 'www.openerp-china.org',
    'maintainer': 'jeff@osbzr.com',
    'website': 'http://openerp-china.org',
    'description': """
Including the following data in the Accounting Standards for Small Business
包含小企业会计准则以下数据

* Chart of Accounts
* 科目表模板

* Account templates
* 科目模板

* Tax templates
* 税金模板

    """,
    'depends': ['l10n_cn'],
    'data': [
        'data/l10n_cn_small_business_chart_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'auto_install': False
}
