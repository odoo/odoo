from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare, float_is_zero

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    sale_line_ids = fields.Many2many(
        comodel_name="sale.order.line",
        relation="account_move_line_sale_order_line_rel",
        column1="move_line_id",
        column2="order_line_id",
        string="Sales Order Lines",
        copy=False,
    )
    sale_line_warn_msg = fields.Text(
        compute="_compute_sale_line_warn_msg",
        depends_context=("uid",),
    )

    @api.depends("product_id.sale_line_warn_msg")
    def _compute_sale_line_warn_msg(self):
        self._compute_warn_msg_from_product(
            "sale_line_warn_msg",
            "sale.group_warning_sale",
        )

    @api.depends("balance", "is_downpayment")
    def _compute_is_storno(self):
        super()._compute_is_storno()
        for line in self:
            if line.is_downpayment:
                line.is_storno = (
                    line.company_id.account_storno
                    and line.company_id.currency_id.compare_amounts(line.balance, 0.0)
                    > 0
                )

    def _get_fields_order_line_link(self):
        return [*super()._get_fields_order_line_link(), "sale_line_ids"]

    def _sale_prepare_order_line_values(self):
        return [
            {
                "product_id": line.product_id.id,
                "product_qty": line.quantity,
                "product_uom_id": line.product_uom_id.id,
                "price_unit": line.price_unit,
                "discount": line.discount,
            }
            for line in self
        ]

    def _get_downpayment_lines(self):
        return self.sale_line_ids.filtered("is_downpayment").invoice_line_ids.filtered(
            lambda line: line.move_id._is_downpayment(),
        )

    def _prepare_analytic_lines(self):
        values_list = super()._prepare_analytic_lines()

        move_to_reinvoice = self.env["account.move.line"]
        if values_list and self._sale_can_be_reinvoiced():
            move_to_reinvoice = self

        if move_to_reinvoice.filtered(
            lambda aml: not aml.move_id.reversed_entry_id and aml.product_id
        ):
            map_sale_line_per_move = (
                move_to_reinvoice._sale_create_reinvoice_sale_line()
            )
            _debug.pipeline(
                "reinvoice_lines_mapped",
                lines=move_to_reinvoice,
                mapped=len(map_sale_line_per_move),
            )
            for values in values_list:
                sale_line = map_sale_line_per_move.get(values.get("move_line_id"))
                if sale_line:
                    values["so_line"] = sale_line.id

        return values_list

    def _filtered_discount_lines(self):
        lines = super()._filtered_discount_lines()
        discount_line_ids = []
        for company, company_lines in self.grouped("company_id").items():
            discount_product = company.sudo().sale_discount_product_id
            if discount_product:
                discount_line_ids.extend(
                    company_lines.filtered(
                        lambda line, discount_product=discount_product: (
                            line.product_id == discount_product
                        )
                    ).ids
                )
        if discount_line_ids:
            lines |= self.browse(discount_line_ids)
        return lines

    def _sale_create_reinvoice_sale_line(self):
        sale_order_map = self._sale_get_order_map()
        sale_line_values_to_create = []
        pending_slot_by_key = {}
        existing_line_by_key = {}
        slot_by_move_line = {}
        sequences = {}

        for move_line in self:
            sale_order = sale_order_map.get(move_line.id)
            if not sale_order:
                continue

            move_line._sale_check_order_accepts_expense(sale_order)
            price = move_line._sale_get_invoice_price(sale_order)

            if not move_line._sale_is_reinvoice_mergeable():
                sale_line_values_to_create.append(
                    move_line._sale_prepare_sale_line_values(
                        sale_order,
                        price,
                        self._sale_take_sequence(sequences, sale_order),
                    )
                )
                slot_by_move_line[move_line.id] = len(sale_line_values_to_create) - 1
                continue

            key = (sale_order.id, move_line.product_id.id, price)
            if key in existing_line_by_key:
                slot_by_move_line[move_line.id] = existing_line_by_key[key]
                continue
            if key in pending_slot_by_key:
                slot_by_move_line[move_line.id] = pending_slot_by_key[key]
                continue

            sale_line = self.env["sale.order.line"].search(  # noqa: E8507 - one probe per distinct (order, product, price); the hit is cached across lines
                [
                    ("order_id", "=", sale_order.id),
                    ("price_unit", "=", price),
                    ("product_id", "=", move_line.product_id.id),
                    ("is_expense", "=", True),
                ],
                limit=1,
            )
            if sale_line:
                existing_line_by_key[key] = sale_line
                slot_by_move_line[move_line.id] = sale_line
                continue

            sale_line_values_to_create.append(
                move_line._sale_prepare_sale_line_values(
                    sale_order, price, self._sale_take_sequence(sequences, sale_order)
                )
            )
            slot = len(sale_line_values_to_create) - 1
            pending_slot_by_key[key] = slot
            slot_by_move_line[move_line.id] = slot

        new_sale_lines = self.env["sale.order.line"].create(sale_line_values_to_create)
        _debug.lifecycle(
            "reinvoice_sale_lines",
            move_lines=self,
            created=new_sale_lines,
            reused=len(existing_line_by_key),
        )

        return {
            move_line_id: (new_sale_lines[slot] if isinstance(slot, int) else slot)
            for move_line_id, slot in slot_by_move_line.items()
        }

    def _sale_take_sequence(self, sequences, order):
        if order.id not in sequences:
            sequences[order.id] = self._sale_get_next_expense_sequence(order)
        sequence = sequences[order.id]
        sequences[order.id] = sequence + 1
        return sequence

    def _sale_is_reinvoice_mergeable(self):
        self.check_singleton()
        return (
            self.product_id.expense_policy == "sales_price"
            and self.product_id.invoice_policy == "transferred"
            and not self.env.context.get("force_split_lines")
        )

    def _sale_check_order_accepts_expense(self, sale_order):
        if sale_order.state == "draft":
            _debug.logic("expense_refused", order=sale_order, reason="draft")
            raise UserError(
                _(
                    "The Sales Order %(order)s to be reinvoiced must be validated before registering expenses.",
                    order=sale_order.name,
                ),
            )
        if sale_order.state == "cancel":
            _debug.logic("expense_refused", order=sale_order, reason="cancelled")
            raise UserError(
                _(
                    "The Sales Order %(order)s to be reinvoiced is cancelled."
                    " You cannot register an expense on a cancelled Sales Order.",
                    order=sale_order.name,
                ),
            )
        if sale_order.locked:
            _debug.logic("expense_refused", order=sale_order, reason="locked")
            raise UserError(
                _(
                    "The Sales Order %(order)s to be reinvoiced is currently locked."
                    " You cannot register an expense on a locked Sales Order.",
                    order=sale_order.name,
                ),
            )

    def _sale_get_order_map(self):
        return {}

    def _sale_prepare_sale_line_values(self, order, price, sequence=None):
        self.check_singleton()
        if sequence is None:
            sequence = self._sale_get_next_expense_sequence(order)
        fpos = order.fiscal_position_id or self.env[
            "account.fiscal.position"
        ].with_company(order.company_id)._get_fiscal_position(order.partner_id)
        product_taxes = self.product_id.taxes_id._filter_taxes_by_company(
            order.company_id
        )
        taxes = fpos.map_tax(product_taxes)
        return {
            "order_id": order.id,
            "name": self.name,
            "sequence": sequence,
            "price_unit": price,
            "tax_ids": [x.id for x in taxes],
            "discount": 0.0,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "product_qty": self.quantity,
            "is_expense": True,
            "analytic_distribution": self.analytic_distribution,
        }

    def _sale_get_next_expense_sequence(self, order):
        last_line = self.env["sale.order.line"].search(
            [("order_id", "=", order.id)], order="sequence desc", limit=1
        )
        return last_line.sequence + 1 if last_line else 100

    def _sale_get_invoice_price(self, order):
        self.check_singleton()

        unit_amount = self.quantity
        amount = (self.credit or 0.0) - (self.debit or 0.0)

        if self.product_id.expense_policy == "sales_price":
            _debug.logic("expense_price", line=self, by="pricelist")
            return order.pricelist_id._get_product_price(
                self.product_id,
                1.0,
                uom=self.product_uom_id,
                date=order.date_order,
            )

        uom_precision_digits = self.env["decimal.precision"].get_precision(
            "Product Unit"
        )
        if float_is_zero(unit_amount, precision_digits=uom_precision_digits):
            _debug.logic("expense_price", line=self, by="zero_quantity")
            return 0.0

        if (
            self.company_id.currency_id
            and amount
            and self.company_id.currency_id == order.currency_id
        ):
            _debug.logic("expense_price", line=self, by="company_currency")
            return self.company_id.currency_id.round(abs(amount / unit_amount))

        price_unit = abs(amount / unit_amount)
        currency_id = self.company_id.currency_id
        if currency_id and currency_id != order.currency_id:
            price_unit = currency_id._convert(
                price_unit,
                order.currency_id,
                order.company_id,
                order.date_order or fields.Date.today(),
            )
        _debug.logic("expense_price", line=self, by="converted", price=price_unit)
        return price_unit

    def _sale_can_be_reinvoiced(self):
        self.check_singleton()
        if self.sale_line_ids:
            return False
        return float_compare(
            self.credit or 0.0,
            self.debit or 0.0,
            precision_rounding=self.company_id.currency_id.rounding,
        ) != 1 and self.product_id.expense_policy not in [False, "no"]
