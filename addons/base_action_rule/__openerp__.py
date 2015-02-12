# -*- coding: utf-8 -*-
{
    'name': 'Automated Action Rules',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
This module allows to implement action rules for any object.
============================================================

Use automated actions to automatically trigger actions for various screens.

**Example:** A lead created by a specific user may be automatically set to a specific
sales team, or an opportunity which still has status pending after 14 days might
trigger an automatic reminder email.
    """,
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'resource', 'mail'],
    'data': [
        'data/base_action_rule_data.xml',
        'views/base_action_rule_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
