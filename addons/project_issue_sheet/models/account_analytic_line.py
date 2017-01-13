#-*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    issue_id = fields.Many2one('project.issue', 'Issue', copy=False)
