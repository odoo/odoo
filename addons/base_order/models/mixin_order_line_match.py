from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class MixinOrderLineMatch(models.AbstractModel):
    _name = "mixin.order.line.match"
    _description = "Order Line & Invoice Line Matching"

    _order_line_table = ""
    _order_table = ""
    _link_rel_table = ""
    _link_field = ""
    _move_types = ()
    _add_wizard_model = ""
    _add_wizard_view = ""
    _add_order_context_key = ""

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
    )

    order_line_id = fields.Many2one(
        comodel_name="mixin.order.line.fields",
        readonly=True,
    )
    order_id = fields.Many2one(
        comodel_name="mixin.order",
        readonly=True,
    )
    aml_id = fields.Many2one(
        comodel_name="account.move.line",
        readonly=True,
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        readonly=True,
    )

    state = fields.Char(readonly=True)
    reference = fields.Char(compute="_compute_reference")

    line_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        readonly=True,
    )
    line_qty = fields.Float(readonly=True)
    qty_invoiced = fields.Float(readonly=True)
    qty_to_invoice = fields.Float(
        string="Qty to invoice",
        readonly=True,
    )
    product_uom_qty = fields.Float(
        compute="_compute_product_uom_qty",
        inverse="_inverse_product_uom_qty",
        readonly=False,
    )

    product_uom_price = fields.Float(
        compute="_compute_product_uom_price",
        inverse="_inverse_product_uom_price",
        readonly=False,
    )
    line_amount_taxexc = fields.Monetary(readonly=True)
    invoiced_amount_taxexc = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amount_untaxed_fields",
    )
    ordered_amount_taxexc = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amount_untaxed_fields",
    )

    @api.depends("line_amount_taxexc", "account_move_id", "order_id")
    def _compute_amount_untaxed_fields(self):
        for line in self:
            line.invoiced_amount_taxexc = (
                line.line_amount_taxexc if line.account_move_id else False
            )
            line.ordered_amount_taxexc = (
                line.line_amount_taxexc if line.order_id else False
            )

    @api.depends("order_id.display_name", "account_move_id.display_name")
    def _compute_reference(self):
        for line in self:
            line.reference = (
                line.order_id.display_name or line.account_move_id.display_name
            )

    @api.depends("product_id.display_name", "aml_id.name", "order_line_id.name")
    def _compute_display_name(self):
        for line in self:
            line.display_name = (
                line.product_id.display_name
                or line.aml_id.name
                or line.order_line_id.name
            )

    @api.depends("product_id", "line_uom_id", "line_qty", "product_uom_id")
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id:
                line.product_uom_qty = line.line_uom_id._get_quantity_in_unit(
                    line.line_qty, line.product_uom_id
                )
            else:
                line.product_uom_qty = line.line_qty

    @api.depends("aml_id.price_unit", "order_line_id.price_unit")
    def _compute_product_uom_price(self):
        for line in self:
            line.product_uom_price = (
                line.aml_id.price_unit if line.aml_id else line.order_line_id.price_unit
            )

    @api.onchange("product_uom_price")
    def _inverse_product_uom_price(self):
        for line in self:
            if line.aml_id:
                _debug.lifecycle("match_price_written", target="aml", line=line.aml_id)
                line.aml_id.price_unit = line.product_uom_price
            else:
                _debug.lifecycle(
                    "match_price_written", target="order_line", line=line.order_line_id
                )
                line.order_line_id.price_unit = line.product_uom_price

    @api.onchange("product_uom_qty")
    def _inverse_product_uom_qty(self):
        for line in self:
            if line.aml_id:
                _debug.lifecycle("match_qty_written", target="aml", line=line.aml_id)
                line.aml_id.quantity = line.product_uom_qty
            else:
                _debug.lifecycle(
                    "match_qty_written", target="order_line", line=line.order_line_id
                )
                previous_price_unit = line.order_line_id.price_unit
                line.order_line_id.product_qty = line.product_uom_qty
                line.order_line_id.price_unit = previous_price_unit

    def action_view_line(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": (
                "account.move" if self.account_move_id else self.order_id._name
            ),
            "view_mode": "form",
            "res_id": (
                self.account_move_id.id if self.account_move_id else self.order_id.id
            ),
        }

    @api.model
    def _action_create_invoice_from_order_lines(self, partner, order_lines):
        if len(order_lines.currency_id) == 1:
            currency = order_lines.currency_id
        elif len(order_lines.company_id) == 1:
            currency = order_lines.company_id.currency_id
        else:
            currency = self.env.company.currency_id
        move = self.env["account.move"].create(
            {
                "move_type": self._move_types[0],
                "partner_id": partner.id,
                "currency_id": currency.id,
            }
        )
        move._add_order_lines(order_lines)
        _debug.lifecycle(
            "invoice_created_from_order_lines",
            partner=partner,
            order_lines=order_lines,
            move=move,
        )
        return move._get_records_action()

    def _get_no_order_line_message(self):
        return _("You must select at least one order line to match or create invoice.")

    def _get_add_to_order_messages(self):
        return {
            "no_invoice_line": _("Select invoice lines to add to an order"),
            "multi_partner": _("Please select invoice lines with the same partner."),
            "multi_order": _("Invoice lines can only be added to one order."),
            "action_name": _("Add to Order"),
        }

    def _action_add_to_order(self):
        messages = self._get_add_to_order_messages()
        if not self or not self.aml_id:
            _debug.logic("add_to_order_refused", reason="no_invoice_line")
            raise UserError(messages["no_invoice_line"])
        partner = self.mapped("partner_id.commercial_partner_id")
        if len(partner) > 1:
            _debug.logic(
                "add_to_order_refused", reason="multiple_partners", partners=partner
            )
            raise UserError(messages["multi_partner"])
        if len(self.order_id) > 1:
            _debug.logic(
                "add_to_order_refused", reason="multiple_orders", orders=self.order_id
            )
            raise UserError(messages["multi_order"])
        context = {
            "default_partner_id": partner.id,
            "dialog_size": "medium",
            "has_products": bool(self.aml_id.product_id),
        }
        if self.order_id:
            context[self._add_order_context_key] = self.order_id.id
        return {
            "type": "ir.actions.act_window",
            "name": messages["action_name"],
            "res_model": self._add_wizard_model,
            "target": "new",
            "views": [(self.env.ref(self._add_wizard_view).id, "form")],
            "context": context,
        }

    def action_match_lines(self):
        if not self.order_line_id:
            _debug.logic("match_refused", reason="no_order_line")
            raise UserError(self._get_no_order_line_message())
        if not self.aml_id:
            _debug.logic("match_creates_invoice", order_lines=self.order_line_id)
            return self._action_create_invoice_from_order_lines(
                self.partner_id, self.order_line_id
            )

        order_lines_by_product = self.order_line_id.grouped("product_id")
        aml_by_product = self.aml_id.grouped("product_id")
        residual_order_lines = self.order_line_id
        residual_account_move_lines = self.aml_id

        for product, order_lines in order_lines_by_product.items():
            matching_invoice_lines = aml_by_product.get(product)
            if not matching_invoice_lines:
                continue

            if len(order_lines) <= 1:
                order_line = order_lines[0]
                _debug.logic(
                    "lines_matched",
                    by="single_order_line",
                    product=product,
                    aml=matching_invoice_lines,
                )
                matching_invoice_lines[self._link_field] = [Command.link(order_line.id)]
                residual_order_lines -= order_line
                residual_account_move_lines -= matching_invoice_lines
            else:
                remaining_order_lines = list(order_lines)
                remaining_aml = list(matching_invoice_lines)

                for order_line in list(remaining_order_lines):
                    currency = (
                        order_line.currency_id
                        or order_line.company_id.currency_id
                        or self.env.company.currency_id
                    )
                    for aml in list(remaining_aml):
                        if (
                            currency.compare_amounts(
                                aml.price_unit, order_line.price_unit
                            )
                            == 0
                        ):
                            _debug.logic(
                                "lines_matched",
                                by="equal_price_unit",
                                order_line=order_line,
                                aml=aml,
                            )
                            aml[self._link_field] = [Command.link(order_line.id)]
                            residual_order_lines -= order_line
                            residual_account_move_lines -= aml
                            remaining_order_lines.remove(order_line)
                            remaining_aml.remove(aml)
                            break

                # Leftover lines of the same product at different prices have
                # no further criterion (qty/date/sequence) to pair them on --
                # positionally zipping them would silently link unrelated
                # order/invoice lines. Leave them unmatched instead, same as
                # the different-product case above.

        if len(residual_move := self.aml_id.move_id) == 1:
            if residual_account_move_lines:
                _debug.lifecycle(
                    "unmatched_invoice_lines_removed", lines=residual_account_move_lines
                )
                residual_account_move_lines.unlink()

            _debug.pipeline(
                "residual_order_lines_added",
                move=residual_move,
                order_lines=residual_order_lines,
            )
            residual_move._add_order_lines(residual_order_lines)
        return None

    @property
    def _table_query(self):
        return SQL(
            "%s UNION ALL %s",
            self._query_order_line(),
            self._query_am_line(),
        )

    @api.model
    def _query_order_line(self):
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_order_line(),
            self._from_order_line(),
            self._where_order_line(),
        )

    @api.model
    def _select_order_line(self):
        return SQL(
            """
            ol.id,
            ol.id AS order_line_id,
            NULL::INTEGER AS aml_id,
            o.company_id,
            ol.partner_id,
            ol.product_id,
            ol.product_qty AS line_qty,
            ol.product_uom_id AS line_uom_id,
            ol.qty_invoiced,
            ol.qty_to_invoice,
            o.id AS order_id,
            NULL::INTEGER AS account_move_id,
            ol.price_subtotal AS line_amount_taxexc,
            o.currency_id,
            o.state
            """,
        )

    @api.model
    def _from_order_line(self):
        return SQL(
            "%s ol LEFT JOIN %s o ON ol.order_id = o.id",
            SQL.identifier(self._order_line_table),
            SQL.identifier(self._order_table),
        )

    @api.model
    def _where_order_line(self):
        return SQL(
            """
            (
                o.state = 'done'
                AND (
                    (
                        (ol.product_qty > ol.qty_invoiced OR ol.qty_to_invoice > 0)
                        AND NOT EXISTS (
                            SELECT 1 FROM %(rel)s rel
                            JOIN account_move_line aml ON rel.move_line_id = aml.id
                            WHERE rel.order_line_id = ol.id
                            AND aml.parent_state = 'draft'
                        )
                    )
                    OR ol.qty_to_invoice < 0
                )
            )
            OR (COALESCE(ol.display_type, '') = '' AND ol.is_downpayment AND ol.qty_invoiced > 0)
            """,
            rel=SQL.identifier(self._link_rel_table),
        )

    @api.model
    def _query_am_line(self):
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_am_line(),
            self._from_am_line(),
            self._where_am_line(),
        )

    @api.model
    def _select_am_line(self):
        return SQL(
            """
            -aml.id AS id,
            NULL::INTEGER AS order_line_id,
            aml.id AS aml_id,
            aml.company_id,
            am.partner_id,
            aml.product_id,
            aml.quantity AS line_qty,
            aml.product_uom_id AS line_uom_id,
            NULL::NUMERIC AS qty_invoiced,
            NULL::NUMERIC AS qty_to_invoice,
            NULL::INTEGER AS order_id,
            am.id AS account_move_id,
            aml.amount_currency AS line_amount_taxexc,
            aml.currency_id,
            aml.parent_state AS state
            """,
        )

    @api.model
    def _from_am_line(self):
        return SQL(
            """
            account_move_line aml
            LEFT JOIN account_move am ON aml.move_id = am.id
            """,
        )

    @api.model
    def _where_am_line(self):
        return SQL(
            """
            aml.display_type = 'product'
            AND am.move_type IN %(move_types)s
            AND aml.parent_state IN ('draft', 'posted')
            AND NOT EXISTS (
                SELECT 1 FROM %(rel)s rel
                WHERE rel.move_line_id = aml.id
            )
            """,
            move_types=tuple(self._move_types),
            rel=SQL.identifier(self._link_rel_table),
        )
