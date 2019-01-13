# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Newsletter Subscribe Button',
    'summary': 'Attract visitors to subscribe to mailing lists',
    'description': """
This module brings a new building block with a mailing list widget to drop on any page of your website.
On a simple click, your visitors can subscribe to mailing lists managed in the Email Marketing app.
    """,
    'version': '1.0',
    'category': 'Website',
    'depends': ['website', 'mass_mailing'],
    'data': [
        'security/mass_mailing_security.xml',
        'views/website_mass_mailing_templates.xml',
        'views/snippets_templates.xml',
        'views/mass_mailing_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
}
