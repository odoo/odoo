# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_vn_auto_send_to_sinvoice = fields.Boolean("Auto-send to SInvoice", default=True)
    l10n_vn_pos_symbol = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string='POS Symbol',
        groups='base.group_system,point_of_sale.group_pos_manager',
        help='This is the symbol that will be used on invoices issued from this POS.',
        compute="_compute_l10n_vn_pos_symbol",
        store=True,
        readonly=False
    )

    @api.depends('company_id.l10n_vn_pos_default_symbol')
    def _compute_l10n_vn_pos_symbol(self):
        for pos_config in self:
            if not pos_config.l10n_vn_pos_symbol and pos_config.company_id.l10n_vn_pos_default_symbol:
                pos_config.l10n_vn_pos_symbol = pos_config.company_id.l10n_vn_pos_default_symbol

    def _load_pos_data(self, data):
        response = super()._load_pos_data(data)

        company_id = self.env.company
        if company_id.country_id.code != 'VN':
            return response

        response['data'][0]['_is_vn_edi_pos_applicable'] = bool(response['data'][0].get('l10n_vn_pos_symbol') or company_id.l10n_vn_pos_default_symbol)

        return response
