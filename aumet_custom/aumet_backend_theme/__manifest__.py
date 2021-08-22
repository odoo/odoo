# -*- coding: utf-8 -*-
# Copyright 2016, 2020 Openworx - Mario Gielissen
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Aumet backend theme",
    "summary": "Aumet backend theme",
    "version": "14.0.0.2",
    "category": "Theme/Backend",

	"description": """
		Override odoo theme to aumet colors and fonts
    """,
	'images':[
        'images/screen.png'
	],
    "author": "Openworx",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'web',
        'web_responsive',

    ],
    "data": [
        'views/assets.xml',
		'views/res_company_view.xml',
		'views/users.xml',
        'views/sidebar.xml',
    ],

    'css': ["static/src/css/aumet.css"],

}
