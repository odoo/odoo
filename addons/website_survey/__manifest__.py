# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Survey',
    'category': 'Website/Website',
    'summary': 'Website module for survey\'s SEO',
    'description': """
Module holding survey's SEO on Website
This module allows each survey's page to get their own SEO
    """,
    'depends': ['survey', 'website'],
    'data': [
        'views/survey_templates.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
