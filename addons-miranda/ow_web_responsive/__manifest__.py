# Copyright 2016-2017 LasLabs Inc.
# Copyright 2018-2019 Alexandre Díaz
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Dependency for backend_theme_v13",
    "summary": "Dependency for backend_theme_v13. This module will be obsolete when web_responsive v13 is available in the Odoo Appstore.",
    "version": "13.0.1.0.0",
    "category": "Hidden",
    "website": "https://github.com/OCA/web",
    "author": "LasLabs, Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'web',
        'mail',
    ],
    "data": [
        'views/assets.xml',
        'views/res_users.xml',
        'views/web.xml',
    ],
    'qweb': [
        'static/src/xml/apps.xml',
        'static/src/xml/form_view.xml',
        'static/src/xml/navbar.xml',
    ],
}
