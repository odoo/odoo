# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'China - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['cn'],
    'version': '1.8',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'openerp-china',
    'maintainer': 'jeff@osbzr.com',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
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

We added the option to print a voucher which will also
print the amount in words (special Chinese characters for numbers)
correctly when the cn2an library is installed. (e.g. with pip3 install cn2an)
    """,
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'views/account_move_view.xml',
        'views/account_report.xml',
        'views/report_voucher.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
