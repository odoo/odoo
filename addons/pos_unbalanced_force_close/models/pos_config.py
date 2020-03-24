# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    allow_force_close = fields.Boolean("Allow closing unbalanced sessions")
    difference_debit_account = fields.Many2one("account.account", string='Difference Debit Account')
    difference_credit_account = fields.Many2one("account.account", string='Difference Credit Account')
