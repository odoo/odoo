# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_vn_edi_pos_default_symbol = fields.Many2one(
        related='company_id.l10n_vn_pos_default_symbol',
        readonly=False,
        string='Default PoS Symbol',
        help='Default Sinvoice Symbol for PoS.',
    )
    pos_l10n_vn_pos_symbol = fields.Many2one(
        related="pos_config_id.l10n_vn_pos_symbol",
        readonly=False,
    )
    pos_l10n_vn_auto_send_to_sinvoice = fields.Boolean(
        related="pos_config_id.l10n_vn_auto_send_to_sinvoice",
        readonly=False,
    )
