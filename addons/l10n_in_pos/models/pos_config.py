# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain

from .ir_sequence import L10N_IN_B2C_SEQUENCE_CODE


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_in_b2c_sequence_id = fields.Many2one(
        'ir.sequence',
        string='B2C Invoice Sequence',
        readonly=True,
        copy=False,
        check_company=True,
        help="Numbers the paid B2C orders of this Point of Sale, e.g. P26/07/000000007.",
    )
    l10n_in_b2c_refund_sequence_id = fields.Many2one(
        'ir.sequence',
        string='B2C Refund Invoice Sequence',
        readonly=True,
        copy=False,
        check_company=True,
        help="Numbers the B2C refunds of this Point of Sale, e.g. R26/07/000000004.",
    )

    def _is_quantities_set(self):
        return self.company_id.l10n_in_gst_registration_type or super()._is_quantities_set()

    def _create_sequences(self):
        super()._create_sequences()
        self._l10n_in_create_b2c_sequences()

    def _l10n_in_create_b2c_sequences(self):
        for config in self:
            if config.company_id.country_code != 'IN':
                continue
            for field_name, prefix_letter, name in (
                ('l10n_in_b2c_sequence_id', 'P', self.env._("PoS B2C Invoice seq - %s", config.name)),
                ('l10n_in_b2c_refund_sequence_id', 'R', self.env._("PoS B2C Refund Invoice seq - %s", config.name)),
            ):
                if not config[field_name]:
                    prefix = f"{prefix_letter}%(y)s/{config.id:02d}/"
                    config[field_name] = self.env['ir.sequence'].sudo().create({
                        'name': name,
                        'prefix': prefix,
                        'padding': self.env['ir.sequence']._l10n_in_get_b2c_padding(prefix, False),
                        'code': L10N_IN_B2C_SEQUENCE_CODE,
                        'implementation': 'no_gap',
                        'use_date_range': True,
                        'company_id': config.company_id.id,
                    })

    @api.model
    def _l10n_in_setup_b2c_sequences(self):
        self._l10n_in_search_by_b2c_sequences([False])._l10n_in_create_b2c_sequences()

    @api.model
    def _l10n_in_search_by_b2c_sequences(self, sequence_ids):
        return self.with_context(active_test=False).search(
            Domain('l10n_in_b2c_sequence_id', 'in', sequence_ids)
            | Domain('l10n_in_b2c_refund_sequence_id', 'in', sequence_ids)
        )
