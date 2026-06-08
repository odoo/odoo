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
    l10n_vn_edi_default_symbol_id = fields.Many2one(
        related='company_id.l10n_vn_edi_symbol_id',
        string='Default Symbol',
        domain="[('company_id', '=', company_id)]",
        groups='base.group_system',
        help='This is the symbol that will be used on invoices by default.',
        readonly=False,
    )

    def action_fetch_symbols(self):
        self.env['l10n_vn_edi_viettel.sinvoice.symbol'].action_fetch_symbols()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
