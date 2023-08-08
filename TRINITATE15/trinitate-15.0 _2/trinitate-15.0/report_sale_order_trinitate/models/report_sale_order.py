# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ReportSaleOrder(models.Model):
    _name = "report_sale_order"
    _description = "Report sale and invoiced"

    def _compute_purchase_price(self):
        for rec in self:
            rec.purchase_price_unit = rec.sale_line_id.purchase_price
            rec.purchase_cost = rec.quantity * rec.purchase_price_unit
            rec.utility = rec.price_total_invoice - rec.purchase_cost
            rec.estimated_commission = rec.utility * 0.09
            if rec.price_total_invoice != 0:
                rec.margin = rec.utility / rec.price_total_invoice

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Line",
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Account Move",
    )
    account_move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Account Move Line",
    )
    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    partial = fields.Text()
    order_id = fields.Many2one(
        related="sale_line_id.order_id",
        store=True,
        string="Order",
    )
    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        store=True,
    )
    date_order = fields.Datetime(
        related="order_id.date_order",
        store=True,
        string="Date order",
    )
    user_id = fields.Many2one(
        related="order_id.user_id",
        store=True,
        string="Vendor",
    )
    create_date = fields.Datetime(
        related="order_id.create_date",
    )
    partner_id = fields.Many2one(related="order_id.partner_id", store=True, string="Client")
    invoice_name = fields.Char(related="account_move_id.name", store=True, string="Invoice No.")
    invoice_date = fields.Date(related="account_move_id.invoice_date", store=True, string="Invoice Date")
    product_id = fields.Many2one(
        related="sale_line_id.product_id",
        store=True,
    )
    product_uom_qty = fields.Float(
        related="sale_line_id.product_uom_qty",
        store=True,
        string="Quantity",
    )
    product_uom = fields.Many2one(
        related="sale_line_id.product_uom",
        store=True,
        string="uoM",
    )
    qty_delivered = fields.Float(
        related="sale_line_id.qty_delivered",
        store=True,
        string="Delivered",
    )
    quantity = fields.Float(
        related="account_move_line_id.quantity",
        store=True,
    )
    street_name = fields.Char(
        related="partner_id.street_name",
        string="Street",
    )
    l10n_mx_edi_colony = fields.Char(
        related="partner_id.l10n_mx_edi_colony",
        string="Cologne",
    )
    city_id = fields.Many2one(
        related="partner_id.city_id",
    )
    state_id = fields.Many2one(
        related="partner_id.state_id",
    )
    zip = fields.Char(
        related="partner_id.zip",
    )
    country_id = fields.Many2one(
        related="partner_id.country_id",
    )
    utility = fields.Float()
    purchase_cost = fields.Float()
    estimated_commission = fields.Float()
    margin = fields.Float()
    purchase_price_unit = fields.Float(
        compute="_compute_purchase_price",
    )
    date_account_move_line = fields.Date(
        related="account_move_line_id.date",
        store=True,
    )
    price_total_invoice = fields.Monetary(
        related="account_move_line_id.price_subtotal",
        store=True,
        currency_field="currency_id",
        string="Total invoice",
    )
