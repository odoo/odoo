# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

"""
account.journal object: activate dedicated credit note sequence by default
"""

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    refund_sequence = fields.Boolean(string='Dedicated Credit Note Sequence', help="Check this box if you don't want to share the same sequence for invoices and credit notes made from this journal", default=True)
