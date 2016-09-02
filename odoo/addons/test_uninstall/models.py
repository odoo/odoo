# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class test_uninstall_model(models.Model):
    """
    This model uses different types of columns to make it possible to test
    the uninstall feature of Odoo.
    """
    _name = 'test_uninstall.model'

    name = fields.Char('Name')
    ref = fields.Many2one('res.users', string='User')
    rel = fields.Many2many('res.users', string='Users')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Each name must be unique.'),
    ]
