# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tw_edi_ecpay_staging_mode = fields.Boolean(string="Staging mode")
    l10n_tw_edi_ecpay_merchant_id = fields.Char(string="MerchantID")
    l10n_tw_edi_ecpay_hashkey = fields.Char(string="Hashkey")
    l10n_tw_edi_ecpay_hashIV = fields.Char(string="HashIV")
    l10n_tw_edi_ecpay_seller_identifier = fields.Char(string="Seller Tax ID Number")

    def _is_ecpay_enabled(self):
        return self.l10n_tw_edi_ecpay_merchant_id and self.l10n_tw_edi_ecpay_hashkey and self.l10n_tw_edi_ecpay_hashIV
