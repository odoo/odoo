# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Test_UninstallModel(models.Model):
    """
    This model uses different types of columns to make it possible to test
    the uninstall feature of Odoo.
    """
    _name = 'test_uninstall.model'
    _description = 'Testing Uninstall Model'

    name = fields.Char('Name')
    ref = fields.Many2one('res.users', string='User')
    rel = fields.Many2many('res.users', string='Users')

    _name_uniq = models.Constraint(
        'unique (name)',
        "Each name must be unique.",
    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    _test_uninstall_res_user_unique_constraint = models.Constraint(
        'unique (password)',
        "Test uninstall unique constraint",
    )
    _test_uninstall_res_user_check_constraint = models.Constraint(
        'check (true)',
        "Test uninstall check constraint",
    )
    _test_uninstall_res_user_exclude_constraint = models.Constraint(
        'exclude (password with =)',
        "Test uninstall exclude constraint",
    )
    _test_uninstall_res_user_exclude_constraint_looooooooooooong_name = models.Constraint(
        'exclude (password with =)',
        "Test uninstall exclude constraint",
    )
