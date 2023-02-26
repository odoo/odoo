# -*- coding: utf-8 -*-
from odoo import models, api, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    loan_id = fields.Many2one('hr.loan', 'Loan Id')
