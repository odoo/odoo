# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'test complete_field',
    'version': '1.0',
    'category': 'Tests',
    'summary': 'Completes the Many2one field based on parent model',
    'description': """
Completes the m2o field ``field`` to match the provided value``key``.
Only returns record references linked from a record of the current model.
    """,
    'depends': ['base'],
    'data': ['security/ir.model.access.csv'],
}
