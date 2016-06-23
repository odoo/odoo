# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'account analytic line'

    issue_id = fields.Many2one('project.issue', string='Issue')
