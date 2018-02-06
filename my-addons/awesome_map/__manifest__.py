# -*- coding: utf-8 -*-
{
    'name': "Map View",

    'summary': "Map visualization view for Odoo web client",
    'description': """
        This module use openstreetmap I think
    """,

    'version': '0.1',
    'depends': ['base_geolocalize'],
    'data': [
        "views/res_partner.xml",
        "views/templates.xml"
    ],
    'qweb': [
        "static/src/xml/map_view.xml",
    ]
}