# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2008-2008 凯源吕鑫 lvxin@gmail.com   <basic chart data>
#                         维智众源 oldrev@gmail.com  <states data>
# Copyright (C) 2012-2012 南京盈通 ccdos@intoerp.com <small business chart>
# Copyright (C) 2008-now  开阖软件 jeff@osbzr.com    < PM and LTS >

{
    'name': '中国小企业会计科目表',
    'version': '1.8',
    'category': 'Localization',
    'author': 'www.openerp-china.org',
    'maintainer': 'jeff@osbzr.com',
    'website': 'http://openerp-china.org',
    'description': """

    科目类型\会计科目表模板\增值税\辅助核算类别\管理会计凭证簿\财务会计凭证簿

    添加中文省份数据

    增加小企业会计科目表

    """,
    'depends': ['l10n_cn'],
    'data': [
        'data/l10n_cn_small_business_chart_data.xml',
        'data/account_chart_template_data.yml',
    ],
}
