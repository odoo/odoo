# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2023 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Type",
        compute="_compute_sale_type_id",
        precompute=True,
        store=True,
        readonly=False,
        states={
            "sale": [("readonly", True)],
            "done": [("readonly", True)],
            "cancel": [("readonly", True)],
        },
        ondelete="restrict",
        copy=True,
        check_company=True,
    )
    # Fields converted to computed writable
    picking_policy = fields.Selection(
        compute="_compute_picking_policy", store=True, readonly=False
    )
    incoterm = fields.Many2one(compute="_compute_incoterm", store=True, readonly=False)
    analytic_account_id = fields.Many2one(
        compute="_compute_analytic_account_id", store=True, readonly=False
    )

    @api.model
    def _default_type_id(self):
        return self.env["sale.order.type"].search(
            [("company_id", "in", [self.env.company.id, False])], limit=1
        )

    @api.model
    def _default_sequence_id(self):
        """We get the sequence in same way the core next_by_code method does so we can
        get the proper default sequence"""
        force_company = self.env.company.id
        return self.env["ir.sequence"].search(
            [
                ("code", "=", "sale.order"),
                "|",
                ("company_id", "=", force_company),
                ("company_id", "=", False),
            ],
            order="company_id",
            limit=1,
        )

    @api.depends("partner_id", "company_id")
    @api.depends_context("partner_id", "company_id", "company")
    def _compute_sale_type_id(self):
        for record in self:
            # Specific partner sale type value
            sale_type = (
                record.partner_id.with_company(record.company_id).sale_type
                or record.partner_id.commercial_partner_id.with_company(
                    record.company_id
                ).sale_type
            )
            # Default user sale type value
            if not sale_type:
                sale_type = record.default_get(["type_id"]).get("type_id", False)
            # Get first sale type value
            if not sale_type:
                sale_type = record._default_type_id()
            record.type_id = sale_type

    @api.depends("type_id")
    def _compute_warehouse_id(self):
        res = super()._compute_warehouse_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.warehouse_id:
                order.warehouse_id = order_type.warehouse_id
        return res

    @api.depends("type_id")
    def _compute_picking_policy(self):
        res = None
        if hasattr(super(), "_compute_picking_policy"):
            res = super()._compute_picking_policy()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.picking_policy:
                order.picking_policy = order_type.picking_policy
        return res

    @api.depends("type_id")
    def _compute_payment_term_id(self):
        res = super()._compute_payment_term_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.payment_term_id:
                order.payment_term_id = order_type.payment_term_id
        return res

    @api.depends("type_id")
    def _compute_pricelist_id(self):
        res = super()._compute_pricelist_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.pricelist_id:
                order.pricelist_id = order_type.pricelist_id
        return res

    @api.depends("type_id")
    def _compute_incoterm(self):
        res = None
        if hasattr(super(), "_compute_incoterm"):
            res = super()._compute_incoterm()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.incoterm_id:
                order.incoterm = order_type.incoterm_id
        return res

    @api.depends("type_id")
    def _compute_analytic_account_id(self):
        res = None
        if hasattr(super(), "_compute_analytic_account_id"):
            res = super()._compute_analytic_account_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.analytic_account_id:
                order.analytic_account_id = order_type.analytic_account_id
        return res

    @api.depends("type_id")
    def _compute_validity_date(self):
        res = super()._compute_validity_date()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.quotation_validity_days:
                order.validity_date = fields.Date.to_string(
                    datetime.now() + timedelta(order_type.quotation_validity_days)
                )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New") and vals.get("type_id"):
                sale_type = self.env["sale.order.type"].browse(vals["type_id"])
                if sale_type.sequence_id:
                    vals["name"] = sale_type.sequence_id.next_by_id(
                        sequence_date=vals.get("date_order")
                    )
        return super().create(vals_list)

    def write(self, vals):
        """A sale type could have a different order sequence, so we could
        need to change it accordingly"""
        if vals.get("type_id"):
            sale_type = self.env["sale.order.type"].browse(vals["type_id"])
            if sale_type.sequence_id:
                for record in self:
                    # An order with a type without sequence would get the default one.
                    # We want to avoid changing the order reference when the new
                    # sequence has the same default sequence.
                    ignore_default_sequence = (
                        not record.type_id.sequence_id
                        and sale_type.sequence_id
                        == record.with_company(record.company_id)._default_sequence_id()
                    )
                    if (
                        record.state in {"draft", "sent"}
                        and record.type_id.sequence_id != sale_type.sequence_id
                        and not ignore_default_sequence
                    ):
                        new_vals = vals.copy()
                        new_vals["name"] = sale_type.sequence_id.next_by_id(
                            sequence_date=vals.get("date_order")
                        )
                        super(SaleOrder, record).write(new_vals)
                    else:
                        super(SaleOrder, record).write(vals)
                return True
        return super().write(vals)

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.type_id.journal_id:
            res["journal_id"] = self.type_id.journal_id.id
        if self.type_id:
            res["sale_type_id"] = self.type_id.id
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    route_id = fields.Many2one(compute="_compute_route_id", store=True, readonly=False)

    @api.depends("order_id.type_id")
    def _compute_route_id(self):
        res = None
        if hasattr(super(), "_compute_route_id"):
            res = super()._compute_route_id()
        for line in self.filtered("order_id.type_id"):
            order_type = line.order_id.type_id
            if order_type.route_id:
                line.route_id = order_type.route_id
        return res
