# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_ecpay_enabled = fields.Boolean(string="Is Ecpay Enabled", compute="_compute_is_ecpay_enabled")

    @api.depends('company_id')
    def _compute_is_ecpay_enabled(self):
        for config in self:
            config.is_ecpay_enabled = config.company_id._is_ecpay_enabled()

    def get_limited_partners_loading(self, offset=0):
        partner_ids = super().get_limited_partners_loading(offset)
        walk_in_customer = self.env.ref('l10n_tw_edi_ecpay_pos.ecpay_default_walk_in_customer', raise_if_not_found=False)
        if self.company_id.account_fiscal_country_id.code == 'TW' and walk_in_customer:
            walk_in_customer_id_tuple = (walk_in_customer.id,)
            if walk_in_customer_id_tuple not in partner_ids:
                partner_ids.append(walk_in_customer_id_tuple)
        return partner_ids

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if read_records and config.company_id.account_fiscal_country_id.code == 'TW':
            walk_in_customer = self.env.ref('l10n_tw_edi_ecpay_pos.ecpay_default_walk_in_customer', raise_if_not_found=False)
            read_records[0]['_tw_walk_in_customer'] = walk_in_customer.id if walk_in_customer else None
        return read_records
