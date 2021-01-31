# -*- coding: utf-8 -*-


{
    'name': 'Odoo Employee Tree',
    'version': '1.0',
    'category': 'OdTree',
    'sequence': 14,
    'license':'LGPL-3',
    'description': """
    display employees in a department tree
    """,
    'author': 'openliu',
    'website': 'http://www.openliu.com',
    'images': [],
    'depends': ['odtree','hr'],
    'qweb': [

    ],
    'data': [
        'views/hr_view.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
