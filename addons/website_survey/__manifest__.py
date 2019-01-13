# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Survey',
    'version': '1.0',
    'category': 'Marketing',
    'description': """
Create beautiful surveys and display them on your website
=========================================================

Use the styling and layout of your website for your surveys.
""",
    'website': 'https://www.odoo.com/page/survey',
    'depends': ['website', 'survey'],
    'data': [
        'views/website_survey_templates.xml',
    ],
    'installable': True,
    'auto_install': True
}
