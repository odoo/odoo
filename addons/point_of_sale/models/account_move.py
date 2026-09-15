from odoo import _, api, fields, models

from ..tools import debug_log as dbg


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "mixin.pos.load"]

    pos_order_ids = fields.One2many(
        comodel_name="pos.order",
        inverse_name="account_move",
    )
    pos_payment_ids = fields.One2many(
        comodel_name="pos.payment",
        inverse_name="account_move_id",
    )
    pos_refunded_invoice_ids = fields.Many2many(
        comodel_name="account.move",
        relation="refunded_invoices",
        column1="refund_account_move",
        column2="original_account_move",
    )
    reversed_pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Reversed POS Order",
        index="btree_not_null",
        help="The pos order that was reverted after closing the session to create an invoice for it.",
    )
    pos_diff_session_id = fields.Many2one(
        comodel_name="pos.session",
        string="POS Closing Difference",
        index="btree_not_null",
        help="Session whose closing produced this payment-method difference entry.",
    )
    pos_diff_payment_method_id = fields.Many2one(
        comodel_name="pos.payment.method",
        string="POS Closing Difference Payment Method",
        index="btree_not_null",
        copy=False,
        help="Payment method whose closing count produced this difference entry.",
    )
    pos_session_ids = fields.One2many(
        comodel_name="pos.session",
        inverse_name="move_id",
        string="POS Sessions",
    )
    pos_order_count = fields.Integer(
        string="POS Order Count",
        compute="_compute_pos_order_count",
    )

    @api.depends("pos_order_ids")
    def _compute_pos_order_count(self):
        for move in self:
            move.pos_order_count = len(move.sudo().pos_order_ids)

    @api.depends("tax_cash_basis_created_move_ids", "pos_session_ids")
    def _compute_always_tax_exigible(self):
        super()._compute_always_tax_exigible()
        for move in self:
            if move.always_tax_exigible or move.tax_cash_basis_created_move_ids:
                continue
            if move.pos_session_ids:
                move.always_tax_exigible = True

    def _stock_account_get_last_step_stock_moves(self):
        stock_moves = super()._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == "out_invoice"):
            stock_moves += (
                invoice.sudo()
                .mapped("pos_order_ids.picking_ids.move_ids")
                .filtered(
                    lambda x: (
                        x.state == "done" and x.location_dest_id.usage == "customer"
                    )
                )
            )
        for invoice in self.filtered(lambda x: x.move_type == "out_refund"):
            stock_moves += (
                invoice.sudo()
                .mapped("pos_order_ids.picking_ids.move_ids")
                .filtered(
                    lambda x: x.state == "done" and x.location_id.usage == "customer"
                )
            )
        return stock_moves

    def _prepare_invoice_lot_rows(self):
        self.check_singleton()

        lot_values = super()._prepare_invoice_lot_rows()

        if self.state == "draft":
            return lot_values

        for order in self.sudo().pos_order_ids:
            for line in order.lines:
                lots = line.pack_lot_ids or False
                if lots:
                    for lot in lots:
                        lot_values.append(
                            {
                                "product_name": lot.product_id.name,
                                "quantity": line.qty
                                if lot.product_id.tracking == "lot"
                                else 1.0,
                                "uom_name": line.product_uom_id.name,
                                "lot_name": lot.lot_name,
                                "pos_lot_id": lot.id,
                            }
                        )

        return lot_values

    def _compute_invoice_payments_widget(self):
        super()._compute_invoice_payments_widget()
        for move in self:
            if move.invoice_payments_widget:
                if move.state == "posted" and move.is_invoice(include_receipts=True):
                    reconciled_partials = move._get_all_reconciled_invoice_partials()
                    for i, reconciled_partial in enumerate(reconciled_partials):
                        counterpart_line = reconciled_partial["aml"]
                        pos_payment = counterpart_line.move_id.sudo().pos_payment_ids[
                            :1
                        ]
                        move.invoice_payments_widget["content"][i].update(
                            {
                                "pos_payment_name": pos_payment.payment_method_id.name,
                            }
                        )

    def _compute_amounts(self):
        super()._compute_amounts()
        for move in self:
            if move.move_type == "entry" and move.reversed_pos_order_id:
                move.amount_total_signed *= -1

    def _compute_is_storno(self):
        super()._compute_is_storno()
        for move in self:
            move.is_storno = move.is_storno or (
                move.company_id.account_storno and move.reversed_pos_order_id
            )

    def action_view_source_pos_orders(self):
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "point_of_sale.action_pos_pos_form"
        )

        if len(self.pos_order_ids) == 1:
            action["views"] = [
                (self.env.ref("point_of_sale.view_pos_pos_form", False).id, "form")
            ]
            action["res_id"] = self.pos_order_ids.id
        else:
            action["domain"] = [("id", "in", self.pos_order_ids.ids)]
        return action

    def action_draft(self):
        if self.sudo().pos_order_ids.filtered(lambda o: o.session_id.state != "closed"):
            dbg.logic.debug(
                "account.move %s reset to draft refused: pos session still open",
                dbg.rec(self),
            )
            self.env.user._bus_send(
                "simple_notification",
                {
                    "type": "danger",
                    "message": _(
                        "You can't reset this invoice to draft because the POS session is still open. Please close the ongoing session first, then try again."
                    ),
                    "sticky": True,
                },
            )
            return False
        return super().action_draft()

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        return result or ["id", "name"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        return False


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_cogs_value(self):
        self.check_singleton()
        if not self.product_id:
            return self.price_unit
        price_unit = super()._get_cogs_value()
        sudo_order = self.move_id.sudo().pos_order_ids
        if sudo_order:
            pos_price_unit = sudo_order._get_pos_anglo_saxon_price_unit(
                self.product_id, self.quantity
            )
            dbg.logic.debug(
                "[order:%s] cogs for %s: pos price %s vs account %s",
                dbg.names(sudo_order, "uuid"),
                dbg.rec(self.product_id),
                pos_price_unit,
                price_unit,
            )
            if not self.product_id.sudo().cost_currency_id.is_zero(pos_price_unit):
                price_unit = pos_price_unit
        return price_unit

    def _compute_name(self):
        amls = self.filtered(lambda l: not l.move_id.pos_session_ids)
        super(AccountMoveLine, amls)._compute_name()
