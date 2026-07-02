# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_vn_edi_username = fields.Char(
        related='company_id.l10n_vn_edi_username',
        readonly=False,
    )
    l10n_vn_edi_password = fields.Char(
        related='company_id.l10n_vn_edi_password',
        readonly=False,
    )

    def action_fetch_symbols(self):
        return self.env['l10n_vn.sinvoice.symbol'].action_fetch_symbols()
