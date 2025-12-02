# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tw_edi_ecpay_staging_mode = fields.Boolean(string="Staging mode", groups="base.group_system")
    l10n_tw_edi_ecpay_merchant_id = fields.Char(string="MerchantID", groups="base.group_system")
    l10n_tw_edi_ecpay_hashkey = fields.Char(string="Hashkey", groups="base.group_system")
    l10n_tw_edi_ecpay_hashIV = fields.Char(string="HashIV", groups="base.group_system")

    def _is_ecpay_enabled(self):
        return bool(self.sudo().l10n_tw_edi_ecpay_merchant_id
                and self.sudo().l10n_tw_edi_ecpay_hashkey
                and self.sudo().l10n_tw_edi_ecpay_hashIV)
