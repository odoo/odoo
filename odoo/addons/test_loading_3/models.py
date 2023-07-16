# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class test_loading_1_model(models.Model):
    """
    This model uses different types of columns to make it possible to test
    the registry loading/upgrading/installing feature.
    """
    _inherit = 'test_loading_1.model'
    _description = 'Testing Loading Model 3'

    name_y = fields.Char('Translated NameY 3', translate=True, index='trigram')
    name_z = fields.Char('Required NameZ 3', default='ValueZ 3 default', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name_x, name_z)', 'Each (name, name_z) must be unique.'),
    ]
