# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
