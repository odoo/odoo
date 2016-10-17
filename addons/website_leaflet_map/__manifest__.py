# -*- coding: utf-8 -*-
{

    'name': "Website Map using Leaflet.js",
    'category': 'Website',
    'version': '1.0',
    'summary': """
        OpenERP Website Map using Leaflet.js and OpenStreetMap tiles""",

    'description': """
OpenERP Website Map with Leaflet.js and OpenStreetMap
=====================================================

This addon can be used in place of website_google_map,
and does not require any API key. It uses Leaflet.js and tiles from
the OpenStreetMap project.

Note it will not geolocalize partners for you, make sure they already are.

Leaflet.js
----------

`Leaflet.js <http://leafletjs.com/>`_ is an open-source JavaScript library
for mobile-friendly interactive maps.

OpenStreetMap
-------------

The `OpenStreetMap <https://www.openstreetmap.org/about>`_ project provides
`Tile servers <https://wiki.openstreetmap.org/wiki/Tiles#Servers>`_ which are used by this addon.

Please `donate <https://donate.openstreetmap.org/>`_ to OpenStreetMap!

    """,

    'author': 'François Revol',

    'depends': ['base_geolocalize', 'website_partner'],
    'data': [
        'views/leaflet_map.xml',
    ],
    'installable': True,
}
