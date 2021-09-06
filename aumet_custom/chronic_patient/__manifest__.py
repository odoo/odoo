# -*- coding: utf-8 -*-
{
    'name': "chronic_patient",
    'summary': """ Add Chronic Patient  in POS Customer Screen""",
    'description': """ """,
    'website': "",
    'category': 'Point of Sale',
    'version': '14.0.0.2',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_partner_view.xml',
        'views/templates.xml',

    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    "auto_install": False,
    "installable": True,
}
