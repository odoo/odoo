# -*- coding: utf-8 -*-
{
    'name': 'Google Maps',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'description': """This module adds a Map button on the partner’s form in order to open its address directly in the Google Maps view""",
    'author': 'BHC & OpenERP',
    'website': 'www.bhc.be',
    'depends': ['base'],
    'init_xml': [],
    'images': ['images/google_map.png','images/map.png','images/earth.png'],
    'update_xml': [
                   'google_map_view.xml',
                  ],
    'demo_xml': [],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: