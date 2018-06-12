# -*- coding: utf-8 -*-
{
    'name': u"Ukraine - Accounting",
    'summary': u"Український бухоблік згідно МСФО",
    'description': u"""
Бухгалтерський облік для України (МСФЗ)
=======================================

Цей модуль дає можливість вести бухгалтерський
облік діяльності підприємства згідно міжнародних
стандартів фінансової звітності.

Встановлюється типовий план рахунків,
який підійде більшості підприємств.
Також буде створено налаштування податків
для обліку ПДВ
    """,
    'author': "Bogdan Lisnenko",
    'category': 'Localization/Account Charts',
    'version': '1.1',
    'depends': ['account'],
    'data': [
        'partner_view.xml',
        'data/account_chart_template.xml',
        'data/account.account.template.csv',
        'data/account_tax_template.xml',
        'data/account_chart_template_config.xml',
        'data/account_chart_template.yml',
    ],
    'installable': True,
}
