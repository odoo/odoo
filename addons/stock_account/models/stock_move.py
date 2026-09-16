from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet, float_is_zero

VALUATION_DICT = {
    "value": 0,
    "quantity": 0,
    "description": False,
}

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(
        string="Update quantities on SO/PO",
        default=True,
        copy=True,
        help="Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    value = fields.Monetary(
        currency_field="company_currency_id",
        copy=False,
        help="The current value of the move. It's zero if the move is not valued.",
    )
    value_justification = fields.Text(
        string="Value Description",
        compute="_compute_value_justifications",
    )
    value_computed_justification = fields.Text(
        string="Computed Value Description",
        compute="_compute_value_justifications",
    )
    value_manual = fields.Monetary(
        string="Manual Value",
        currency_field="company_currency_id",
        compute="_compute_value_manual",
        inverse="_inverse_value_manual",
    )
    standard_price = fields.Float(compute="_compute_standard_price")

    price_unit = fields.Float(string="Price Unit")
    is_in = fields.Boolean(
        string="Is Incoming (valued)",
        compute="_compute_is_in",
        store=True,
    )
    is_out = fields.Boolean(
        string="Is Outgoing (valued)",
        compute="_compute_is_out",
        store=True,
    )
    is_dropship = fields.Boolean(
        compute="_compute_is_dropship",
        store=True,
    )
    is_valued = fields.Boolean(compute="_compute_is_valued")
    valued_qty = fields.Float(
        string="Valued Quantity",
        min_display_digits="Product Unit",
        compute="_compute_valued_qty",
        store=True,
        help="The quantity `value` was computed over, in the product's unit of"
        " measure: the picked, company-owned lines crossing a valuation boundary.",
    )

    remaining_qty = fields.Float(
        string="Remaining Quantity",
        compute="_compute_remaining_qty",
        search="_search_remaining_qty",
    )
    remaining_value = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_remaining_value",
    )

    analytic_account_line_ids = fields.Many2many(
        comodel_name="account.analytic.line",
        copy=False,
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Valuation Entry",
        index="btree_not_null",
        copy=False,
    )

    def _search_remaining_qty(self, operator, value):
        if operator != "=" or not isinstance(value, bool) or value is not True:
            raise UserError(
                _("Only is set (= True) is supported in search for remaining_qty.")
            )
        products = (
            "default_product_id" in self.env.context
            and self.env["product.product"].browse(
                self.env.context["default_product_id"]
            )
        ) or self.env["product.product"]
        if not products:
            products = self.env["product.product"].search(
                [("is_storable", "=", True), ("qty_available", ">", 0)]
            )
        if products:
            products = products.browse(
                product.id
                for [product] in self.env["stock.move"]._read_group(
                    [
                        ("product_id", "in", products.ids),
                        ("is_in", "=", True),
                        ("company_id", "in", self.env.companies.ids),
                    ],
                    groupby=["product_id"],
                )
            )
        move_ids = []
        for company in self.env.companies:
            for qty_by_move in (
                products.with_company(company)._get_remaining_moves().values()
            ):
                move_ids.extend(move.id for move in qty_by_move)
        return [("id", "in", move_ids)]

    @api.depends("product_id.standard_price")
    def _compute_standard_price(self):
        for move in self:
            move.standard_price = move.product_id.with_company(
                move.company_id
            ).standard_price

    @api.depends("state", "move_line_ids")
    def _compute_is_in(self):
        for move in self:
            if move.state != "done":
                move.is_in = False
                continue
            move.is_in = move._is_in()

    @api.depends("state", "move_line_ids")
    def _compute_is_out(self):
        for move in self:
            if move.state != "done":
                move.is_out = False
                continue
            move.is_out = move._is_out()

    @api.depends("state")
    def _compute_is_dropship(self):
        for move in self:
            if move.state != "done":
                move.is_dropship = False
                continue
            move.is_dropship = move._is_dropshipped() or move._is_dropshipped_returned()

    @api.depends("is_in", "is_out")
    def _compute_is_valued(self):
        for move in self:
            move.is_valued = move.is_in or move.is_out

    @api.depends("state", "move_line_ids")
    def _compute_valued_qty(self):
        for move in self:
            move.valued_qty = move._get_valued_qty() if move.state == "done" else 0.0

    def _recompute_valuation_flags(self):
        for field_name in ("is_in", "is_out", "is_dropship", "valued_qty"):
            self.env.add_to_compute(self._fields[field_name], self)
        self.invalidate_recordset(["is_valued"])

    @api.depends("value")
    def _compute_value_manual(self):
        for move in self:
            move.value_manual = move.value

    @api.depends("value", "is_in", "is_out")
    def _compute_value_justifications(self):
        self.value_justification = False
        self.value_computed_justification = False
        for move in self:
            if not move.is_in:
                if move.is_out:
                    move.value_justification = move._get_out_value_justification()
                continue
            move.value_justification = move._get_value_data()["description"]
            computed_value_data = move._get_value_data(ignore_manual_update=True)
            if computed_value_data["description"] == move.value_justification:
                move.value_computed_justification = False
            else:
                value = move.company_currency_id.format(computed_value_data["value"])
                move.value_computed_justification = self.env._(
                    "Computed value: %(value)s\n%(description)s",
                    value=value,
                    description=computed_value_data["description"],
                )

    @api.depends("quantity", "product_id.stock_move_ids.value")
    def _compute_remaining_qty(self):
        for company, moves in self.grouped("company_id").items():
            products = moves.product_id
            remaining_by_product = products.with_company(company)._get_remaining_moves()

            for move in moves:
                move.remaining_qty = remaining_by_product.get(move.product_id, {}).get(
                    move, 0
                )

    @api.depends(
        "value",
        "remaining_qty",
        "product_id.standard_price",
        "move_line_ids.lot_id.standard_price",
    )
    def _compute_remaining_value(self):
        for move in self:
            if not move.is_in:
                move.remaining_value = 0
                continue
            valued_qty = move._get_valued_qty()
            ratio = move.remaining_qty / valued_qty if valued_qty else 0
            if move.product_id.cost_method == "fifo":
                move.remaining_value = ratio * move.value if ratio else 0
            elif move.product_id.lot_valuated:
                qty = sum(move.move_line_ids.mapped("quantity_product_uom"))
                if qty:
                    unit_cost = (
                        sum(
                            (
                                move_line.lot_id.standard_price
                                or move.product_id.standard_price
                            )
                            * move_line.quantity_product_uom
                            for move_line in move.move_line_ids
                        )
                        / qty
                    )
                else:
                    unit_cost = move.product_id.standard_price
                move.remaining_value = move.remaining_qty * unit_cost
            else:
                move.remaining_value = move.remaining_qty * move.standard_price

    def _inverse_picked(self):
        super()._inverse_picked()
        self.sudo()._create_analytic_move()

    def _inverse_value_manual(self):
        for move in self:
            if move.value_manual == move.value:
                continue
            self.env["product.value"].sudo().create(
                {
                    "move_id": move.id,
                    "value": move.value_manual,
                    "company_id": move.company_id.id,
                }
            )

    def action_adjust_valuation(self):
        if len(self) != 1:
            raise UserError(_("You can only adjust valuation for one move at a time."))
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "stock_account.product_value_action"
        )
        product = self.product_id if len(self.product_id) == 1 else False
        if product:
            action["name"] = _(
                "Adjust Valuation: %(product)s", product=product.display_name
            )
        action["target"] = "new"
        action["context"] = {
            "default_move_id": self.id,
        }
        return action

    def _action_done(self, cancel_backorder=False):
        moves_out = self.filtered(lambda m: m._is_out())
        _debug.pipeline("valuation_done_enter", moves=self, outgoing=moves_out)
        moves_out._set_value()
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        moves_out = moves_out.exists()
        moves_in = moves.filtered(lambda m: m.is_in or m.is_dropship)
        _debug.pipeline(
            "valuation_done_split",
            incoming=moves_in,
            outgoing=moves_out,
            vanished=len(self) - len(moves),
        )
        moves_in.with_context(
            std_price_incremental_recompute=not moves_out
        )._set_value()
        moves._create_account_move()
        moves_out.product_id.filtered(
            lambda p: (
                p.cost_method == "fifo"
                or (p.cost_method == "average" and p.lot_valuated)
            )
        )._update_standard_price()
        (moves_in | moves_out).sudo()._create_analytic_move()
        return moves

    def _get_valuation_accounts(self, cache=None):
        self.check_singleton()
        template = self.product_id.product_tmpl_id
        key = (template.id, self.company_id.id)
        if cache is not None and key in cache:
            return cache[key]
        accounts = template.with_company(self.company_id)._get_product_accounts()
        if cache is not None:
            cache[key] = accounts
        return accounts

    def _get_stock_journal(self, accounts=None):
        self.check_singleton()
        if accounts is None:
            accounts = self._get_valuation_accounts()
        return accounts["stock_journal"] or self.company_id.account_stock_journal_id

    def _create_account_move(self):
        accounts_cache = {}
        moves_by_entry = defaultdict(lambda: self.env["stock.move"])
        for move in self:
            if move._is_account_move_required():
                key = (
                    move.company_id,
                    move._get_partner_id_for_valuation_lines(),
                    move._get_stock_journal(
                        move._get_valuation_accounts(accounts_cache)
                    ),
                )
                moves_by_entry[key] |= move

        _debug.pipeline(
            "account_moves_grouped",
            moves=self,
            entries=len(moves_by_entry),
        )
        account_moves = self.env["account.move"].sudo()
        for (company, partner_id, journal), moves in moves_by_entry.items():
            if not journal:
                _debug.logic(
                    "account_move_refused",
                    reason="no_stock_journal",
                    company=company.id,
                    moves=moves,
                )
                raise UserError(
                    self.env._(
                        "No inventory valuation journal is set for company"
                        " %(company)s. Set one in the inventory settings, or on the"
                        " product category.",
                        company=company.display_name,
                    )
                )
            aml_vals_list = []
            for move in moves:
                aml_vals_list += move._prepare_account_move_line_vals(
                    accounts=move._get_valuation_accounts(accounts_cache)
                )
            if not aml_vals_list:
                _debug.logic(
                    "account_move_skipped",
                    reason="no_aml_vals",
                    moves=moves,
                    journal=journal.id,
                )
                continue

            joined_refs = ", ".join(sorted(set(moves.mapped("reference")) - {False}))
            if len(joined_refs) > 43:
                joined_refs = joined_refs[:40] + "..."

            account_move = (
                self.env["account.move"]
                .sudo()
                .with_company(company)
                .create(
                    {
                        "ref": joined_refs,
                        "partner_id": partner_id,
                        "journal_id": journal.id,
                        "line_ids": [
                            Command.create(aml_vals) for aml_vals in aml_vals_list
                        ],
                        "date": self.env.context.get("force_period_date")
                        or fields.Date.context_today(self),
                    }
                )
            )
            moves.account_move_id = account_move.id
            account_move._post()
            _debug.lifecycle(
                "account_move_created",
                entry=account_move.id,
                journal=journal.id,
                moves=moves,
                lines=len(aml_vals_list),
            )
            account_moves |= account_move
        return account_moves

    def _get_partner_id_for_valuation_lines(self):
        self.check_singleton()
        return self.picking_id.partner_id.commercial_partner_id.id or False

    def _create_analytic_move(self):
        for move in self:
            analytic_line_vals = move._update_analytic_lines()
            if analytic_line_vals:
                move.analytic_account_line_ids += (
                    self.env["account.analytic.line"].sudo().create(analytic_line_vals)
                )
                _debug.lifecycle(
                    "analytic_lines_created",
                    move=move.id,
                    lines=len(analytic_line_vals),
                )

    def _prepare_account_move_line_vals(self, accounts=None):
        if accounts is None:
            accounts = self._get_valuation_accounts()
        source_acc = self.location_id.valuation_account_id
        dest_acc = self.location_dest_id.valuation_account_id
        if source_acc and dest_acc:
            debit_acc, credit_acc = dest_acc, source_acc
        elif source_acc:
            debit_acc = accounts["stock_valuation"]
            credit_acc = source_acc
        else:
            debit_acc = dest_acc
            credit_acc = accounts["stock_valuation"]
        if not debit_acc or not credit_acc:
            raise UserError(
                self.env._(
                    "No stock valuation account is configured for product"
                    " %(product)s. Set one on its product category, or in the"
                    " company's inventory settings.",
                    product=self.product_id.display_name,
                )
            )
        value = self._get_aml_value()
        return [
            {
                "account_id": credit_acc.id,
                "name": self.reference + " - " + self.product_id.name,
                "debit": 0,
                "credit": value,
                "product_id": self.product_id.id,
            },
            {
                "account_id": debit_acc.id,
                "name": self.reference + " - " + self.product_id.name,
                "debit": value,
                "credit": 0,
                "product_id": self.product_id.id,
            },
        ]

    def _get_aml_value(self):
        self.check_singleton()
        return self.value

    def _get_analytic_distribution(self):
        return {}

    def _get_price_unit(self):
        if len(self.product_id) > 1:
            return 0
        total_value = sum(self.mapped("value"))
        total_qty = sum(m._get_valued_qty() for m in self)
        return total_value / total_qty if total_qty else 0

    def _get_cogs_price_unit(self, quantity=0):

        if len(self.product_id) > 1:
            return 0
        total_qty = sum(m._get_valued_qty() * (-1 if m.is_in else 1) for m in self)
        valued_consigned_qty = self._get_valued_consigned_qty()
        total_valued_qty = total_qty + valued_consigned_qty
        if total_valued_qty and (
            self.product_id.cost_method == "fifo"
            or valued_consigned_qty
            or (
                self.product_id.lot_valuated
                and self.product_id.cost_method == "average"
            )
        ):
            total_value = sum(m.value * (-1 if m.is_in else 1) for m in self)
            _debug.logic(
                "cogs_price_unit",
                by="valued_layers",
                product=self.product_id.id,
                qty=total_valued_qty,
                value=total_value,
            )
            return total_value / total_valued_qty
        else:
            _debug.logic(
                "cogs_price_unit",
                by="standard_price",
                product=self.product_id.id,
                qty=total_valued_qty,
            )
            return self.product_id.standard_price

    def _set_value(self, correction_quantity=None):
        fifo_qty_processed = defaultdict(float)
        _debug.pipeline("set_value_enter", moves=self, correction=correction_quantity)

        if self:
            present = {
                move.id
                for (move,) in self.env["product.value"]
                .sudo()
                ._read_group([("move_id", "in", self.ids)], ["move_id"])
            }
            prescan = {mid: mid in present for mid in self.ids}
            self = self.with_context(_manual_value_prescan=prescan)

        for company, moves in self.grouped("company_id").items():
            products_to_recompute = set()
            lots_to_recompute = set()
            extra_value_by_product = defaultdict(float)
            extra_qty_by_product = defaultdict(float)

            for move in moves:
                move = move.with_company(company.id)
                if move.is_dropship or move.is_in:
                    products_to_recompute.add(move.product_id.id)
                    if move.product_id.lot_valuated:
                        if any(not ml.lot_id for ml in move.move_line_ids):
                            _debug.logic(
                                "valuation_refused",
                                reason="lot_required",
                                move=move.id,
                                product=move.product_id.id,
                            )
                            raise UserError(
                                self.env._(
                                    "A lot/serial number is required for product '%s' as it has lot valuation enabled.",
                                    move.product_id.display_name,
                                )
                            )
                        lots_to_recompute.update(move.move_line_ids.lot_id.ids)
                if move.is_in:
                    move.value = move.sudo()._get_value()
                    _debug.logic("move_valued", move=move.id, by="in")
                    if (
                        self.env.context.get("std_price_incremental_recompute")
                        and move.product_id.is_storable
                    ):
                        extra_value_by_product[move.product_id] += move.value
                        extra_qty_by_product[move.product_id] += move._get_valued_qty()
                    continue
                if not move._is_out():
                    if not (move.is_in or move.is_dropship) and move.value:
                        _debug.logic("move_value_cleared", move=move.id)
                        move.value = 0
                        products_to_recompute.add(move.product_id.id)
                        if move.product_id.lot_valuated:
                            lots_to_recompute.update(move.move_line_ids.lot_id.ids)
                    continue
                manual_data = move.sudo()._get_manual_value(move._get_valued_qty())
                if manual_data["quantity"]:
                    move.value = manual_data["value"]
                    _debug.logic("move_valued", move=move.id, by="manual")
                    continue
                if correction_quantity:
                    previous_qty = move._get_valued_qty() - correction_quantity
                    ratio = correction_quantity / previous_qty if previous_qty else 0
                    move.value += ratio * move.value
                    _debug.logic("move_valued", move=move.id, by="correction")
                    continue
                if move.product_id.lot_valuated:
                    value = 0.0
                    for move_line in move.move_line_ids:
                        lot_price = move_line.lot_id.standard_price
                        if not lot_price:
                            lot_price = move.product_id.standard_price
                        value += lot_price * move_line.quantity_product_uom
                    move.value = value
                    _debug.logic("move_valued", move=move.id, by="lot_cost")
                    continue

                if move.product_id.cost_method == "fifo":
                    valued_qty = move._get_valued_qty()
                    move.value = move.product_id.with_context(
                        fifo_qty_already_processed=fifo_qty_processed[move.product_id]
                    )._run_fifo(valued_qty)
                    fifo_qty_processed[move.product_id] += valued_qty
                    _debug.logic("move_valued", move=move.id, by="fifo")
                else:
                    move.value = move.product_id.standard_price * move._get_valued_qty()
                    _debug.logic("move_valued", move=move.id, by="standard_price")

            _debug.pipeline(
                "standard_price_recompute",
                company=company.id,
                products=len(products_to_recompute),
                lots=len(lots_to_recompute),
            )
            self.env["product.product"].browse(products_to_recompute).with_company(
                company
            )._update_standard_price(
                extra_value=extra_value_by_product,
                extra_quantity=extra_qty_by_product,
            )
            self.env["stock.lot"].browse(lots_to_recompute).with_company(
                company
            )._update_standard_price()

    def _get_value(
        self, forced_std_price=False, at_date=False, ignore_manual_update=False
    ):
        return self._get_value_data(forced_std_price, at_date, ignore_manual_update)[
            "value"
        ]

    def _get_value_data(
        self,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False,
    ):
        self.check_singleton()

        valued_qty = remaining_qty = self._get_valued_qty()
        value = 0
        add_extra_value = True
        descriptions = []

        if not ignore_manual_update:
            manual_data = self._get_manual_value(remaining_qty, at_date)
            if manual_data["quantity"]:
                add_extra_value = False
            value += manual_data["value"]
            remaining_qty -= manual_data["quantity"]
            if manual_data.get("description"):
                descriptions.append(manual_data["description"])

        if remaining_qty:
            account_data = self._get_value_from_account_move(remaining_qty, at_date)
            value += account_data["value"]
            remaining_qty -= account_data["quantity"]
            if account_data.get("description"):
                descriptions.append(account_data["description"])

        if remaining_qty:
            production_data = self._get_value_from_production(remaining_qty, at_date)
            value += production_data["value"]
            remaining_qty -= production_data["quantity"]
            if production_data.get("description"):
                descriptions.append(production_data["description"])

        if remaining_qty:
            quotation_data = self._get_value_from_quotation(remaining_qty, at_date)
            value += quotation_data["value"]
            remaining_qty -= quotation_data["quantity"]
            if quotation_data.get("description"):
                descriptions.append(quotation_data["description"])

        if remaining_qty:
            return_data = self._get_value_from_returns(remaining_qty, at_date)
            value += return_data["value"]
            remaining_qty -= return_data["quantity"]
            if return_data.get("description"):
                descriptions.append(return_data["description"])

        if remaining_qty:
            std_price_data = self._get_value_from_std_price(
                remaining_qty, forced_std_price, at_date
            )
            value += std_price_data["value"]
            descriptions.append(std_price_data.get("description"))

        if add_extra_value:
            extra_data = self._get_value_from_extra(valued_qty, at_date)
            value += extra_data["value"]
            if extra_data.get("description"):
                descriptions.append(extra_data["description"])

        _debug.logic(
            "move_value_resolved",
            move=self.id,
            product=self.product_id.id,
            valued_qty=valued_qty,
            unsourced_qty=remaining_qty,
            value=value,
            sources=len(descriptions),
        )
        return {
            "value": value,
            "quantity": valued_qty,
            "description": "\n".join(descriptions),
        }

    def _get_out_value_justification(self):
        self.check_singleton()
        quantity = self._get_valued_qty()
        manual_data = self.sudo()._get_manual_value(quantity)
        if manual_data["quantity"]:
            return manual_data["description"]
        uom = self.product_id.uom_id.name
        if self.product_id.lot_valuated:
            return self.env._(
                "%(quantity)s %(uom)s at each lot's cost", quantity=quantity, uom=uom
            )
        if self.product_id.cost_method == "fifo":
            return self.env._(
                "%(quantity)s %(uom)s off the FIFO stack", quantity=quantity, uom=uom
            )
        return self.env._(
            "%(quantity)s %(uom)s at product's cost", quantity=quantity, uom=uom
        )

    def _get_valued_qty(self, lot=None):
        self.check_singleton()
        if self._is_in():
            return sum(self._get_in_move_lines(lot).mapped("quantity_product_uom"))
        if self._is_out():
            return sum(self._get_out_move_lines(lot).mapped("quantity_product_uom"))
        if self.is_dropship:
            lines = self.move_line_ids
            if lot:
                lines = lines.filtered(lambda ml: ml.lot_id == lot)
            return sum(lines.mapped("quantity_product_uom"))
        return 0

    def _get_manual_value(self, quantity, at_date=None):
        valuation_data = dict(VALUATION_DICT)
        if not at_date:
            prescan = self.env.context.get("_manual_value_prescan")
            if prescan is not None and prescan.get(self.id) is False:
                return valuation_data
        domain = Domain([("move_id", "=", self.id)])
        if at_date:
            domain &= Domain([("date", "<=", at_date)])
        manual_value = (
            self.env["product.value"]
            .sudo()
            .search(domain, order="date desc, id desc", limit=1)
        )
        if manual_value:
            valuation_data["value"] = manual_value.value
            valuation_data["quantity"] = quantity
            description = _(
                "Adjusted on %(date)s by %(user)s",
                date=manual_value.date,
                user=manual_value.user_id.name,
            )
            if manual_value.description:
                description += "\n" + manual_value.description
            valuation_data["description"] = description
        return valuation_data

    def _get_value_from_account_move(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_value_from_production(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_value_from_quotation(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_value_from_returns(self, quantity, at_date=None):
        if self.origin_returned_move_id and self.origin_returned_move_id.is_out:
            origin_move = self.origin_returned_move_id
            origin_valued_qty = origin_move._get_valued_qty()
            return {
                "value": 0
                if self.product_uom_id.is_zero(origin_valued_qty)
                else origin_move.value * quantity / origin_valued_qty,
                "quantity": quantity,
                "description": _(
                    "Value based on original move %(reference)s",
                    reference=origin_move.reference,
                ),
            }
        return dict(VALUATION_DICT)

    def _get_value_from_std_price(self, quantity, std_price=False, at_date=None):
        if at_date and self.product_id.cost_method == "standard":
            std_price = std_price or self.product_id._get_standard_price_at_date(
                at_date
            )
        elif self.product_id.lot_valuated and len(self.lot_ids) == 1:
            std_price = self.lot_ids.standard_price
        elif (
            not std_price
            and at_date
            and self.product_id.cost_method in ("fifo", "average")
        ):
            valued_qty = self._get_valued_qty()
            if valued_qty:
                std_price = self.value / valued_qty
        return {
            "value": (std_price or self.product_id.standard_price) * quantity,
            "quantity": quantity,
            "description": self.env._(
                "%(quantity)s %(uom)s at product's cost",
                quantity=quantity,
                uom=self.product_id.uom_id.name,
            ),
        }

    def _get_value_from_extra(self, quantity, at_date=None):
        return dict(VALUATION_DICT)

    def _get_valued_move_lines(self, incoming, lot=None):
        res = OrderedSet()
        for move_line in self.move_line_ids:
            if lot and move_line.lot_id != lot:
                continue
            if not move_line.picked:
                continue
            if move_line._is_excluded_from_valuation():
                continue
            from_valued = move_line.location_id._is_valuation_required()
            to_valued = move_line.location_dest_id._is_valuation_required()
            if (
                (not from_valued and to_valued)
                if incoming
                else (from_valued and not to_valued)
            ):
                res.add(move_line.id)
        return self.env["stock.move.line"].browse(res)

    def _get_in_move_lines(self, lot=None):
        return self._get_valued_move_lines(True, lot=lot)

    def _is_in(self):
        self.check_singleton()
        return self._get_in_move_lines() and not self._is_dropshipped_returned()

    def _get_out_move_lines(self, lot=None):
        return self._get_valued_move_lines(False, lot=lot)

    def _is_out(self):
        self.check_singleton()
        return self._get_out_move_lines() and not self._is_dropshipped()

    def _is_dropshipped(self):
        self.check_singleton()
        return (
            self.location_id.usage == "supplier"
            or (self.location_id.usage == "transit" and not self.location_id.company_id)
        ) and (
            self.location_dest_id.usage == "customer"
            or (
                self.location_dest_id.usage == "transit"
                and not self.location_dest_id.company_id
            )
        )

    def _is_dropshipped_returned(self):
        self.check_singleton()
        return (
            self.location_id.usage == "customer"
            or (self.location_id.usage == "transit" and not self.location_id.company_id)
        ) and (
            self.location_dest_id.usage == "supplier"
            or (
                self.location_dest_id.usage == "transit"
                and not self.location_dest_id.company_id
            )
        )

    def _is_incoming(self):
        return super()._is_incoming() and not self._is_dropshipped()

    def _is_outgoing(self):
        return super()._is_outgoing() and not self._is_dropshipped_returned()

    def _update_analytic_lines(self):
        self.check_singleton()
        if not self._get_analytic_distribution() and not self.analytic_account_line_ids:
            return False

        if self.state in ["cancel", "draft"]:
            return False
        amount, unit_amount = 0, 0

        if self.state != "done":
            if self.picked:
                unit_amount = self.product_uom_id._get_quantity_in_unit(
                    self.quantity, self.product_id.uom_id
                )
                amount = unit_amount * self.product_id.standard_price
            else:
                return False
        else:
            amount = self.value
            unit_amount = self._get_valued_qty()

        if self._is_out():
            amount = -amount

        if self.analytic_account_line_ids and amount == 0 and unit_amount == 0:
            self.analytic_account_line_ids.unlink()
            return False

        return self.env["account.analytic.account"]._perform_analytic_distribution(
            self._get_analytic_distribution(),
            amount,
            unit_amount,
            self.analytic_account_line_ids,
            self,
        )

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        self.check_singleton()
        return {
            "name": self.reference,
            "amount": amount,
            **account_field_values,
            "unit_amount": unit_amount,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_id.uom_id.id,
            "company_id": self.company_id.id,
            "ref": self._description,
            "category": "other",
        }

    def _is_account_move_required(self):
        self.check_singleton()
        _debug.logic(
            "account_move_required_inputs",
            move=self.id,
            storable=self.product_id.is_storable,
            valued=self.is_valued,
            valuation=self.product_id.valuation,
            src_account=self.location_id.valuation_account_id,
            dest_account=self.location_dest_id.valuation_account_id,
        )
        return bool(
            self.product_id.is_storable
            and self.is_valued
            and (
                self.location_dest_id.valuation_account_id
                or self.location_id.valuation_account_id
            )
            and not float_is_zero(
                self.quantity, precision_rounding=self.product_uom_id.rounding
            )
            and self.product_id.valuation == "real_time"
        )

    def _is_excluded_from_valuation(self):
        self.check_singleton()
        return (
            self.restrict_partner_id
            and self.restrict_partner_id != self.company_id.partner_id
        )

    def _get_related_invoices(self):
        return self.env["account.move"]

    def _get_valued_consigned_qty(self):
        consigned_lines = self.move_line_ids.filtered(
            lambda l: l._is_consigned_valued_line()
        )
        return sum(
            sml.quantity_product_uom
            * (-1 if sml.location_dest_id._is_valuation_required() else 1)
            for sml in consigned_lines
        )
