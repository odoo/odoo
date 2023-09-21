# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.constrains('prefix', 'suffix')
    def _validate_sequence_number(self):
        journal_ids = self.env['account.journal'].search([('restrict_mode_hash_table', '=', True), ('secure_sequence_id', 'in', self.ids)])
        prefix = journal_ids.mapped('secure_sequence_id.prefix')
        suffix = journal_ids.mapped('secure_sequence_id.suffix')

        if any(seq and not seq.isdigit() for seq in (prefix + suffix)):
            raise ValidationError(_("The prefix and suffix for this sequence should only be positive numbers."))
