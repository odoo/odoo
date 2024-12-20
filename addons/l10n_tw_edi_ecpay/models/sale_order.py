# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_tw_edi_is_print = fields.Boolean(string="Print")
    l10n_tw_edi_is_donate = fields.Boolean(string="Donate")
    l10n_tw_edi_love_code = fields.Char(string="Love Code")
    l10n_tw_edi_customer_name = fields.Char(string="Customer Name", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_customer_address = fields.Char(string="Customer Address", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_customer_email = fields.Char(string="Customer Email", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_customer_phone = fields.Char(string="Customer Phone", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_customer_identifier = fields.Char(string="Tax ID Number", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[("1", "ECpay e-invoice carrier"), ("2", "Citizen Digital Certificate"), ("3", "Mobile Barcode")],
    )
    l10n_tw_edi_carrier_number = fields.Char(string="Carrier Number")

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res.update(
            {
                "l10n_tw_edi_customer_identifier": self.l10n_tw_edi_customer_identifier,
                "l10n_tw_edi_is_print": self.l10n_tw_edi_is_print,
                "l10n_tw_edi_is_donate": self.l10n_tw_edi_is_donate,
                "l10n_tw_edi_love_code": self.l10n_tw_edi_love_code,
                "l10n_tw_edi_customer_address": self.l10n_tw_edi_customer_address,
                "l10n_tw_edi_customer_name": self.l10n_tw_edi_customer_name,
                "l10n_tw_edi_customer_email": self.l10n_tw_edi_customer_email,
                "l10n_tw_edi_customer_phone": self.l10n_tw_edi_customer_phone,
                "l10n_tw_edi_carrier_type": self.l10n_tw_edi_carrier_type,
                "l10n_tw_edi_carrier_number": self.l10n_tw_edi_carrier_number,
            }
        )
        return res

    @api.depends('partner_id')
    def _compute_customer_info(self):
        for order in self:
            order.l10n_tw_edi_customer_identifier = order.partner_id.vat
            order.l10n_tw_edi_customer_name = order.partner_id.name
            order.l10n_tw_edi_customer_address = order.partner_id.contact_address
            order.l10n_tw_edi_customer_email = order.partner_id.email
            order.l10n_tw_edi_customer_phone = order.partner_id.phone
