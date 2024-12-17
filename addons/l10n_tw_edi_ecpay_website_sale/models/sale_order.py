# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_tw_edi_is_print = fields.Boolean(string="Print")
    l10n_tw_edi_love_code = fields.Char(string="Love Code")
    l10n_tw_edi_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[("1", "ECpay e-invoice carrier"), ("2", "Citizen Digital Certificate"), ("3", "Mobile Barcode")],
    )
    l10n_tw_edi_carrier_number = fields.Char(string="Carrier Number")

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res.update(
            {
                "l10n_tw_edi_is_print": self.l10n_tw_edi_is_print,
                "l10n_tw_edi_love_code": self.l10n_tw_edi_love_code,
                "l10n_tw_edi_carrier_type": self.l10n_tw_edi_carrier_type,
                "l10n_tw_edi_carrier_number": self.l10n_tw_edi_carrier_number,
            }
        )
        return res
