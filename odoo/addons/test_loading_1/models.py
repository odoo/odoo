# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class test_loading_1_model(models.Model):
    """
    This model uses different types of columns to make it possible to test
    the registry loading/upgrading/installing feature.
    """
    _name = 'test_loading_1.model'
    _description = 'Testing Loading Model 1'

    name_x = fields.Char('NameX 1')
    name_y = fields.Char('NameY 1')

    _sql_constraints = [
        ('name_uniq', 'unique (name_x)', 'Each name_x must be unique.'),
    ]
