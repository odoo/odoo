# -*- coding: utf-8 -*-
# Copyright 2016-2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Web Responsive",
    "summary": "It provides a mobile compliant interface for Odoo Community "
               "web",
    "version": "10.0.1.1.0",
    "category": "Website",
    "website": "https://laslabs.com/",
    "author": "LasLabs, Tecnativa, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'web',
    ],
    "data": [
        'views/assets.xml',
        'views/web.xml',
    ],
    'qweb': [
        'static/src/xml/form_view.xml',
        'static/src/xml/navbar.xml',
    ],
}
