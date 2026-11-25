# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError, ValidationError

L10N_IN_B2C_NUMBER_LENGTH = 16
L10N_IN_B2C_SEQUENCE_CODE = 'l10n_in_pos.b2c_invoice'


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.constrains('code', 'prefix', 'suffix', 'padding')
    def _check_l10n_in_b2c_number_length(self):
        for sequence in self:
            if sequence.code != L10N_IN_B2C_SEQUENCE_CODE:
                continue
            padding = self._l10n_in_get_b2c_padding(sequence.prefix, sequence.suffix)
            if sequence.padding != padding:
                raise ValidationError(self.env._(
                    "GST invoice numbers must be %(length)s characters long: set the Sequence Size of %(sequence)s to %(padding)s.",
                    length=L10N_IN_B2C_NUMBER_LENGTH, sequence=sequence.name, padding=padding,
                ))

    @api.constrains('prefix')
    def _check_l10n_in_b2c_prefix_unique_per_config(self):
        b2c_sequences = self.filtered(lambda seq: seq.code == L10N_IN_B2C_SEQUENCE_CODE)
        if not b2c_sequences:
            return
        configs = self.env['pos.config']._l10n_in_search_by_b2c_sequences(b2c_sequences.ids).filtered(
            lambda config: config.l10n_in_b2c_sequence_id._get_prefix_suffix()[0]
            == config.l10n_in_b2c_refund_sequence_id._get_prefix_suffix()[0],
        )
        if configs:
            raise ValidationError(self.env._(
                'The B2C invoice and refund invoice sequences of a Point of Sale must have different prefixes: %s',
                ', '.join(configs.mapped('name')),
            ))

    def write(self, vals):
        if 'prefix' not in vals and 'suffix' not in vals:
            return super().write(vals)
        b2c_sequences = self.filtered(lambda seq: vals.get('code', seq.code) == L10N_IN_B2C_SEQUENCE_CODE)
        b2c_sequences_by_padding = b2c_sequences.grouped(lambda seq: self._l10n_in_get_b2c_padding(
            vals.get('prefix', seq.prefix), vals.get('suffix', seq.suffix),
        ))
        for padding, sequences in b2c_sequences_by_padding.items():
            super(IrSequence, sequences).write({**vals, 'padding': padding})
        return super(IrSequence, self - b2c_sequences).write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_l10n_in_b2c_sequence(self):
        if configs := self.env['pos.config']._l10n_in_search_by_b2c_sequences(self.ids):
            raise UserError(self.env._(
                "You cannot delete a B2C invoice sequence used by a Point of Sale: %s",
                ", ".join(configs.mapped('name')),
            ))

    @api.model
    def _l10n_in_get_b2c_padding(self, prefix, suffix):
        prefix, suffix = self.new({'prefix': prefix, 'suffix': suffix})._get_prefix_suffix()
        return L10N_IN_B2C_NUMBER_LENGTH - len(prefix + suffix)
