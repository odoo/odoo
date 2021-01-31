# -*- coding: utf-8 -*-
##############################################################################
#
#    odtree
#    author:15251908@qq.com (openliu)
#    license:'LGPL-3
#
##############################################################################

{
    'name': 'Odoo Tree',
    'version': '1.0',
    'category': 'OdTree',
    'sequence': 14,
    'license':'LGPL-3',
    'description': """
    Custom Tree Structure In ListView or KanbanView ,
    eg: Product category tree ,Department tree
    """,
    'author': 'openliu',
    'website': 'http://www.openliu.com',
    'images': [],
    'depends': ['web'],
    'qweb': [
        "static/src/xml/odtree.xml",
    ],
    'data': [
        'views/odtree_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
