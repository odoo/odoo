# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    followup_line_id = fields.Many2one('followup.line', 'Follow-up Level')
    followup_date = fields.Date('Latest Follow-up')
    result = fields.Float(compute='_get_result', string="Balance Amount")

    def _get_result(self):
        for aml in self:
            aml.result = aml.debit - aml.credit
