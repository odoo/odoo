# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2008-2008 凯源吕鑫 lvxin@gmail.com   <basic chart data>
#                         维智众源 oldrev@gmail.com  <states data>
# Copyright (C) 2012-2012 南京盈通 ccdos@intoerp.com <small business chart>
# Copyright (C) 2008-now  开阖软件 jeff@osbzr.com    < PM and LTS >
# Copyright (C) 2019-now  浪潮PS Cloud lizheng02@inspur.com    < PM and LTS >

{
    'name': 'China - Small Business CoA',
    'version': '2.0',
    'category': 'Localization',
    'author': 'www.openerp-china.org,lizheng02@inspur.com',
    'maintainer': 'lizheng02@inspur.com',
    'website': 'http://www.mypscloud.com',
    'description': """

    科目类型\会计科目表模板\增值税\辅助核算类别\管理会计凭证簿\财务会计凭证簿

    添加中文省份数据

    增加小企业会计科目表

    修改小企业会计科目表
    
    修改小企业会计税率

    """,
    'depends': ['l10n_cn'],
    'data': [
        'data/l10n_cn_small_business_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_cn_small_business_chart_post_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'auto_install': True
}
