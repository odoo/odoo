# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    consolidation_journal_line_ids = fields.Many2many('consolidation.journal.line', string="Consolidation Journal Line")
