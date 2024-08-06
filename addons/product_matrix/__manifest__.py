# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Product Matrix",
    'summary': """
       Technical module: Matrix Implementation
    """,
    'description': """
Please refer to Sale Matrix or Purchase Matrix for the use of this module.
    """,
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['account'],
    # Account dependency for section_and_note widget.
    'qweb': [
        "static/src/xml/product_matrix.xml",
    ],
    'data': [
        'views/assets.xml',
        'views/matrix_templates.xml',
    ],
    'demo': [
        'data/product_matrix_demo.xml',
    ],
    'license': 'LGPL-3',
}
