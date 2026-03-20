# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_tw_edi_is_print = fields.Boolean(
        string="Get Printed Version",
        compute="_compute_is_print",
        store=True,
        readonly=False,
    )
    l10n_tw_edi_love_code = fields.Char(
        string="Love Code",
        compute="_compute_love_code",
        store=True,
        readonly=False,
    )
    l10n_tw_edi_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[
            ("1", "ECPay E-Invoice Carrier"),
            ("2", "Citizen Digital Certificate"),
            ("3", "Mobile Barcode"),
            ("4", "EasyCard"),
            ("5", "iPass"),
        ],
        copy=False,
        readonly=False,
        compute="_compute_carrier_info",
        store=True,
        help="""- Citizen Digital Certificate: The carrier number format is 2 capital letters following 14 digits.
        - Mobile Barcode: The carrier number format is / following 7 alphanumeric or +-. string.
        - EasyCard or iPass: The carrier number is the card hidden code, the carrier number 2 is the card visible code.
        """
    )
    l10n_tw_edi_carrier_number = fields.Char(
        string="Carrier Number",
        compute="_compute_carrier_info",
        store=True,
        copy=False,
        readonly=False,
    )
    l10n_tw_edi_carrier_number_2 = fields.Char(
        string="Carrier Number 2",
        compute="_compute_carrier_info",
        store=True,
        copy=False,
        readonly=False,
    )
    l10n_tw_edi_so_ecpay_tab_invisible = fields.Boolean(
        compute='_compute_l10n_tw_edi_so_ecpay_tab_invisible',
        help="Make ECPay tab invisible on Sale Order form view for B2B customers or when ECPay is not enabled.",
    )

    @api.depends("l10n_tw_edi_love_code", "l10n_tw_edi_carrier_type", "partner_id")
    def _compute_is_print(self):
        for order in self:
            if order.l10n_tw_edi_love_code or (order.partner_id.vat and order.l10n_tw_edi_carrier_type in [1, 2]):
                order.l10n_tw_edi_is_print = False

    @api.depends("l10n_tw_edi_is_print", "l10n_tw_edi_carrier_type", "partner_id")
    def _compute_love_code(self):
        for order in self:
            if order.l10n_tw_edi_is_print or order.l10n_tw_edi_carrier_type or order.partner_id.vat:
                order.l10n_tw_edi_love_code = False

    @api.depends("l10n_tw_edi_is_print", "l10n_tw_edi_love_code")
    def _compute_carrier_info(self):
        for order in self:
            if order.l10n_tw_edi_is_print or order.l10n_tw_edi_love_code:
                order.l10n_tw_edi_carrier_type = False
                order.l10n_tw_edi_carrier_number = False
                order.l10n_tw_edi_carrier_number_2 = False

    @api.depends("partner_id")
    def _compute_l10n_tw_edi_so_ecpay_tab_invisible(self):
        for order in self:
            order.l10n_tw_edi_so_ecpay_tab_invisible = order.partner_id.commercial_partner_id.is_company or not (
                        order.company_id.country_id.code == 'TW' and order.company_id._is_ecpay_enabled())

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
