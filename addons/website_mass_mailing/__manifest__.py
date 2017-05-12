# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Mass Mailing Campaigns',
    'description': """
Add a snippet in the website builder to subscribe a mass_mailing list
    """,
    'version': '1.0',
    'category': 'Marketing',
    'depends': ['website', 'mass_mailing'],
    'data': [
        'security/mass_mailing_security.xml',
        'views/website_mass_mailing_templates.xml',
        'views/unsubscribe_templates.xml',
        'views/snippets_templates.xml',
        'views/mass_mailing_view.xml',
        'views/res_config_view.xml',
    ],
    'auto_install': True,
}
