# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-2018 CodUP (<http://codup.com>).
#
##############################################################################

{
    'name': 'Russia - Accounting',
    'version': '3.1',
    'summary': 'План счетов РФ',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Russia in OpenERP.
==============================================================================
Возможности:

  - План счетов бухгалтерского учёта финансово-хозяйственной деятельности организаций, утверждённый Приказом Минфина РФ от 31.10.2000 года № 94н
    """,
    'author': 'CodUP',
    'website': 'http://codup.com',
    'license': 'AGPL-3',
    'depends': ['account'],
    'demo': [],
    'data': [
        'data/account_chart.xml',
        'data/account.account.template.csv',
        'data/account_chart_template.xml',
        'data/account_tax_template.xml',
        'data/account_chart_template_data.xml',
    ],
    'images': ['static/description/banner.png'],
    'sequence': 1,
    'installable': True,
}
