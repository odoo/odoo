# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tw_edi_ecpay_api_url = fields.Char(string="API URL")
    l10n_tw_edi_ecpay_merchant_id = fields.Char(string="MerchantID")
    l10n_tw_edi_ecpay_hashkey = fields.Char(string="Hashkey")
    l10n_tw_edi_ecpay_hashIV = fields.Char(string="HashIV")
    l10n_tw_edi_ecpay_seller_identifier = fields.Char(string="Seller Tax ID Number")
    l10n_tw_edi_ecpay_allowance_domain = fields.Char(string="Ecpay Allowance Domain")

    def _l10n_tw_edi_prepare_api_param(self):
        if not (self.l10n_tw_edi_ecpay_api_url and self.l10n_tw_edi_ecpay_merchant_id and self.l10n_tw_edi_ecpay_hashkey and self.l10n_tw_edi_ecpay_hashIV):
            raise UserError(_("Please fill in the ECpay API information in the company setting!"))
        return self.l10n_tw_edi_ecpay_api_url, self.l10n_tw_edi_ecpay_merchant_id, self.l10n_tw_edi_ecpay_hashkey, self.l10n_tw_edi_ecpay_hashIV
