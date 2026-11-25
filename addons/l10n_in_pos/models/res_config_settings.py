# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_l10n_in_b2c_sequence_prefix = fields.Char(
        related='pos_config_id.l10n_in_b2c_sequence_id.prefix',
        string='Invoice Sequence',
        readonly=False,
    )
    pos_l10n_in_b2c_refund_sequence_prefix = fields.Char(
        related='pos_config_id.l10n_in_b2c_refund_sequence_id.prefix',
        string='Refund Invoice Sequence',
        readonly=False,
    )
