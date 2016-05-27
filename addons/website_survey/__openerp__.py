# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Website Survey',
    'version': '1.0',
    'category': 'Marketing',
    'complexity': 'easy',
    'website': 'https://www.odoo.com/page/survey',
    'description': """
Website - Survey (bridge module)
=================================================================================
This module adds a Survey design button inside survey views and all website features
""",
    'depends': ['website', 'survey'],
    'data': [
        'views/website_survey_templates.xml',
        'views/website_survey.xml',
    ],
    'installable': True,
    'auto_install': True
}
