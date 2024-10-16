# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons import base


class Test_UninstallModel(models.Model):
    """
    This model uses different types of columns to make it possible to test
    the uninstall feature of Odoo.
    """
    _description = 'Testing Uninstall Model'

    name = fields.Char('Name')
    ref = fields.Many2one('res.users', string='User')
    rel = fields.Many2many('res.users', string='Users')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Each name must be unique.'),
    ]


class ResUsers(base.ResUsers):

    _sql_constraints = [
        ('test_uninstall_res_user_unique_constraint', 'unique (password)', 'Test uninstall unique constraint'),
        ('test_uninstall_res_user_check_constraint', 'check (true)', 'Test uninstall check constraint'),
        ('test_uninstall_res_user_exclude_constraint', 'exclude (password with =)', 'Test uninstall exclude constraint'),
        ('test_uninstall_res_user_exclude_constraint_looooooooooooong_name', 'exclude (password with =)', 'Test uninstall exclude constraint'),
    ]
