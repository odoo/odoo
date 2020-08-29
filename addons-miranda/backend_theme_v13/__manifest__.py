# -*- coding: utf-8 -*-
# Copyright 2016, 2019 Openworx - Mario Gielissen
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Openworx Material Backend Theme V13",
    "summary": "Openworx Material Backend Theme V13",
    "version": "13.0.0.1",
    "category": "Theme/Backend",
    "website": "http://www.openworx.nl",
	"description": """
		Openworx Material Backend theme for Odoo 13.0 community edition.
    """,
	'images':[
        'images/screen.png'
	],
    "author": "Openworx",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'web',
        'ow_web_responsive',

    ],
    "data": [
        'views/assets.xml',
		'views/res_company_view.xml',
		#'views/users.xml',
        #'views/sidebar.xml',
    ],
    #'live_test_url': 'https://youtu.be/JX-ntw2ORl8'

}

