# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_ecpay_enabled = fields.Boolean(string="Is Ecpay Enabled", compute="_compute_is_ecpay_enabled")

    @api.depends('company_id')
    def _compute_is_ecpay_enabled(self):
        for config in self:
            config.is_ecpay_enabled = config.company_id._is_ecpay_enabled()

    def get_limited_partners_loading(self):
        partner_ids = super().get_limited_partners_loading()
        walk_in_customer = self.env.ref('l10n_tw_edi_ecpay_pos.ecpay_default_walk_in_customer', raise_if_not_found=False)
        if walk_in_customer and walk_in_customer.id not in partner_ids:
            partner_ids.append((walk_in_customer.id,))
        return partner_ids
