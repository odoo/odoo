# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_tw_edi_is_print = fields.Boolean(string="Print")
    l10n_tw_edi_love_code = fields.Char(string="Love Code")
    l10n_tw_edi_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[
            ("1", "Member Account"),
            ("2", "Citizen Digital Certificate"),
            ("3", "Mobile Barcode"),
            ("4", "EasyCard"),
            ("5", "iPass"),
        ],
    )
    l10n_tw_edi_carrier_number = fields.Char(string="Carrier Number")
    l10n_tw_edi_carrier_number_2 = fields.Char(string="Carrier Number 2")

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.company_id.country_id.code == 'TW' and self.company_id._is_ecpay_enabled():
            res.update(
                {
                    "l10n_tw_edi_is_print": self.l10n_tw_edi_is_print,
                    "l10n_tw_edi_love_code": self.l10n_tw_edi_love_code,
                    "l10n_tw_edi_carrier_type": self.l10n_tw_edi_carrier_type,
                    "l10n_tw_edi_carrier_number": self.l10n_tw_edi_carrier_number,
                    "l10n_tw_edi_carrier_number_2": self.l10n_tw_edi_carrier_number_2,
                }
            )
        return res
