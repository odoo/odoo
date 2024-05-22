# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer Portal',
    'summary': 'Customer Portal',
    'sequence': '9000',
    'category': 'Hidden',
    'description': """
This module adds required base code for a fully integrated customer portal.
It contains the base controller class and base templates. Business addons
will add their specific templates and controllers to extend the customer
portal.

This module contains most code coming from odoo v10 website_portal. Purpose
of this module is to allow the display of a customer portal without having
a dependency towards website editing and customization capabilities.""",
    'depends': ['web', 'web_editor', 'http_routing', 'mail', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        'data/portal_data.xml',
        'views/assets.xml',
        'views/portal_templates.xml',
        'wizard/portal_share_views.xml',
        'wizard/portal_wizard_views.xml',
    ],
    'qweb': [
        'static/src/xml/portal_chatter.xml',
        'static/src/xml/portal_signature.xml',
    ],
    'license': 'LGPL-3',
}
