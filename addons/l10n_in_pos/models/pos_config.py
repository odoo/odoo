# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_in_b2c_invoice_prefix = fields.Char(
        string='B2C Invoice Prefix',
        default='P',
        required=True,
        copy=False,
        help='Uppercase letter (other than R) used as prefix of the B2C invoice numbers. R is reserved for refunds.',
    )
    l10n_in_b2c_invoice_seq_id = fields.Many2one('ir.sequence', string='B2C Invoice Sequence', readonly=True, copy=False, check_company=True)
    l10n_in_b2c_refund_seq_id = fields.Many2one('ir.sequence', string='B2C Credit Note Sequence', readonly=True, copy=False, check_company=True)

    @api.constrains('l10n_in_b2c_invoice_prefix')
    def _check_l10n_in_b2c_invoice_prefix(self):
        for config in self:
            if not re.fullmatch(r'[A-Z]', config.l10n_in_b2c_invoice_prefix):
                raise ValidationError(self.env._('Use one uppercase letter for the B2C invoice prefix.'))
            if config.l10n_in_b2c_invoice_prefix == 'R':
                raise ValidationError(self.env._('The B2C invoice prefix "R" is reserved for refunds. Use another letter.'))

    def _create_sequences(self):
        res = super()._create_sequences()
        self.filtered(lambda config: config.company_id.country_code == 'IN')._l10n_in_create_b2c_invoice_sequences()
        return res

    def _l10n_in_create_b2c_invoice_sequences(self):
        sequence_vals = {
            'code': 'pos.order',
            'padding': 7,
            'implementation': 'no_gap',
        }
        for config in self:
            for field_name, sequence_name in (
                ('l10n_in_b2c_invoice_seq_id', self.env._('PoS B2C invoices of %s', config.name)),
                ('l10n_in_b2c_refund_seq_id', self.env._('PoS B2C credit notes of %s', config.name)),
            ):
                if not config[field_name]:
                    config[field_name] = self.env['ir.sequence'].sudo().create({
                        **sequence_vals,
                        'name': sequence_name,
                        'company_id': config.company_id.id,
                    })

    def _l10n_in_get_b2c_invoice_sequence(self, is_refund):
        self.ensure_one()
        # Configs created before this feature have no B2C invoice sequences yet.
        self.sudo()._l10n_in_create_b2c_invoice_sequences()
        return self.l10n_in_b2c_refund_seq_id if is_refund else self.l10n_in_b2c_invoice_seq_id

    @api.ondelete(at_uninstall=True)
    def _l10n_in_unlink_b2c_invoice_sequences(self):
        (self.l10n_in_b2c_invoice_seq_id | self.l10n_in_b2c_refund_seq_id).sudo().unlink()

    def _is_quantities_set(self):
        return self.company_id.l10n_in_gst_registration_type or super()._is_quantities_set()
