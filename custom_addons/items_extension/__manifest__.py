# -*- coding: utf-8 -*-
{
    'name': "Items Extension",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'depends': ['base','stock', 'global_utilities', 'product'],
    'data': [
        'views/product_template_extension.xml',
        'views/product_template_hide_fields.xml',
        'views/product_list_extension.xml',
    ],
    'installable': True,
    'application':True,
}

