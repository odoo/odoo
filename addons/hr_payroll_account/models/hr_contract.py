# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContract(models.Model):

    _inherit = 'hr.contract'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    journal_id = fields.Many2one('account.journal', string='Salary Journal')
