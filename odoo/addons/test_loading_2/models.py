# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class test_loading_1_model(models.Model):
    """
    This model uses different types of columns to make it possible to test
    the registry loading/upgrading/installing feature.
    """
    _inherit = 'test_loading_1.model'
    _description = 'Testing Loading Model 2'

    name_x = fields.Char('NameX 2')
    name_y = fields.Char('NameY 2')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name_x, name_y)', 'Each (name, name_y) must be unique.'),
    ]
