# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
    l10n_vn_edi_default_symbol = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string='Default Symbol',
        groups='base.group_system',
        help='This is the symbol that will be used on partners that do not have a specific symbol on them.',
        compute='_compute_l10n_vn_edi_default_symbol',
        inverse='_inverse_l10n_vn_edi_default_symbol',
    )

    @api.depends('company_id')
    def _compute_l10n_vn_edi_default_symbol(self):
        ResPartner = self.env['res.partner']
        l10n_vn_edi_symbol_field = ResPartner._fields['l10n_vn_edi_symbol']
        self.l10n_vn_edi_default_symbol = l10n_vn_edi_symbol_field.get_company_dependent_fallback(ResPartner)

    def _inverse_l10n_vn_edi_default_symbol(self):
        for setting in self:
            self.env['ir.default'].set(
                'res.partner',
                'l10n_vn_edi_symbol',
                setting.l10n_vn_edi_default_symbol.id,
                company_id=setting.company_id.id
            )
