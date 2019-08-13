# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class IrSequence(models.Model):

    _inherit = 'ir.sequence'

    l10n_cl_journal_ids = fields.Many2many('account.journal', relation='l10n_cl_journal_sequence_rel',
                                           string='Journals', readonly=True)

