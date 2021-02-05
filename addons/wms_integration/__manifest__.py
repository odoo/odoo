# -*- coding: utf-8 -*-
{
    'name': "wms_integration",

    'summary': """
        Модуль для интеграции wms с данной ERP or lavka.yandex.ru""",

    'description': """
        Модуль для интеграции wms с данной ERP 
    """,

    'author': "viktor-shved",
    'website': "https://lavka.yandex.ru",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Internal integraions',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['product', 'purchase', 'sale', 'stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
