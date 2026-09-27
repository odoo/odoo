# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_vn_edi_send_transfer_note = fields.Boolean(
        related='company_id.l10n_vn_edi_send_transfer_note',
        readonly=False,
    )
    l10n_vn_edi_stock_default_sinvoice_symbol_id = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        related='company_id.l10n_vn_edi_stock_default_sinvoice_symbol_id',
        readonly=False,
    )
