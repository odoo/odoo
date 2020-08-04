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
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'www.openerp-china.org',
    'maintainer': 'jeff@osbzr.com',
    'website': 'http://openerp-china.org',
    'description': """
Includes the following data for the Chinese localization
========================================================

Account Type/科目类型

State Data/省份数据

    科目类型\会计科目表模板\增值税\辅助核算类别\管理会计凭证簿\财务会计凭证簿

    添加中文省份数据

    增加小企业会计科目表

    修改小企业会计科目表

    修改小企业会计税率

    """,
    'depends': ['base', 'account', 'l10n_multilang'],
    'data': [
        'data/account_tax_group_data.xml',
        'data/l10n_cn_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_cn_chart_post_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_data.xml',
        'views/account_move_view.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
}
