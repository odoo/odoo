# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    sequence_id = fields.Many2one('ir.sequence', string='Entry Sequence',
                                  help='This field contains the information related to the numbering of the journal entries of this journal.',
                                  copy=False, check_company=True)
    refund_sequence_id = fields.Many2one('ir.sequence', string='Credit Note Entry Sequence',
                                         help='This field contains the information related to the numbering of the credit note entries of this journal.',
                                         copy=False, check_company=True)
