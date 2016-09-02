# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Automated Action Rules',
    'version': '1.0',
    'category': 'Sales',
    'description': """
This module allows to implement action rules for any object.
============================================================

Use automated actions to automatically trigger actions for various screens.

**Example:** A lead created by a specific user may be automatically set to a specific
sales team, or an opportunity which still has status pending after 14 days might
trigger an automatic reminder email.
    """,
    'depends': ['base', 'resource', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/base_action_rule_data.xml',
        'views/base_action_rule_view.xml',
    ],
    'demo': [
        'data/base_action_rule_demo.xml',
    ],
}
