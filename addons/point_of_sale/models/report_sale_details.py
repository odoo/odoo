from datetime import UTC, timedelta
from itertools import starmap

from odoo import _, api, fields, models
from odoo.fields import Domain

from ..tools import debug_log as dbg


class ReportPoint_Of_SaleReport_Saledetails(models.AbstractModel):
    _name = "report.point_of_sale.report_saledetails"
    _description = "Point of Sale Details"

    @api.model
    @dbg.timed
    def get_sale_details(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        **kwargs,
    ):
        """Report selected sales; reconcile drawers only for complete sessions."""
        if not session_ids:
            date_start, date_stop = self._get_date_start_and_date_stop(
                date_start, date_stop
            )

        domain = self._get_domain_orders(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )
        orders = self.env["pos.order"].search(domain)
        configs, sessions = self._get_report_scope(
            config_ids, session_ids, date_start, date_stop
        )
        currency = self._get_report_currency(configs)
        companies = configs.company_id or self.env.company
        dbg.pipeline.debug(
            "[report] sale details %s..%s configs=%s sessions=%s -> %s in %s",
            date_start,
            date_stop,
            dbg.rec(configs),
            dbg.rec(sessions),
            dbg.rec(orders),
            currency.name,
        )

        with dbg.timer(self.env, "[report] sales totals over %d orders", len(orders)):
            sales = self._get_sales_totals(orders, currency)
        with dbg.timer(self.env, "[report] counted payments"):
            payments = self._get_counted_payments(orders, sessions)
            self._update_payment_rows_with_report_currency(
                payments, orders, sessions, currency
            )

        data = {
            "state": sessions.state if len(sessions) == 1 else "multiple",
            "date_start": sessions.start_at
            if session_ids and len(sessions) == 1
            else date_start,
            "date_stop": sessions.stop_at
            if session_ids and len(sessions) == 1
            else date_stop,
            "session_name": sessions.name if len(sessions) == 1 else False,
            "opening_note": sessions.opening_notes if len(sessions) == 1 else False,
            "closing_note": sessions.closing_notes if len(sessions) == 1 else False,
            "config_names": configs.mapped("name"),
            "company_id": companies.id if len(companies) == 1 else False,
            "company_name": ", ".join(companies.mapped("name")),
            "nbr_orders": len(orders),
            "currency": {
                "symbol": currency.symbol,
                "position": currency.position == "after",
                "total_paid": currency.round(sales["total"]),
                "precision": currency.decimal_places,
            },
            "discount_number": sales["discount_number"],
            "discount_amount": sales["discount_amount"],
            **self._prepare_products_section(configs, sales["sold"], sales["refunded"]),
            **self._prepare_payments_section(payments, session_ids),
            **self._prepare_invoice_section(orders, currency),
        }
        return self._finalize_sale_details(data, orders, configs, sessions)

    def _finalize_sale_details(self, data, orders, configs, sessions):
        """Extend a report using its resolved selection instead of searching again."""
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        data.update(
            {
                "session_ids": data.get("session_ids")
                or (
                    docids
                    if not data.get("config_ids")
                    and not data.get("date_start")
                    and not data.get("date_stop")
                    else None
                ),
                "config_ids": data.get("config_ids"),
                "date_start": data.get("date_start"),
                "date_stop": data.get("date_stop"),
            }
        )
        args, kwargs = self._prepare_get_sale_details_args_kwargs(data)
        dbg.lifecycle.debug(
            "[report] _get_report_values docids=%s data keys=%s", docids, dbg.keys(data)
        )
        data.update(self.get_sale_details(*args, **kwargs))
        return data

    def _prepare_get_sale_details_args_kwargs(self, data):
        args = (
            data["date_start"],
            data["date_stop"],
            data["config_ids"],
            data["session_ids"],
        )
        return args, {}

    def _get_date_start_and_date_stop(self, date_start, date_stop):
        default_start = not date_start
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            today = fields.Datetime.from_string(
                fields.Date.context_today(self)
            ).replace(tzinfo=self.env.tz)
            date_start = today.astimezone(UTC).replace(tzinfo=None)

        # Add a calendar day before converting: DST days are not 24 hours.
        default_stop = (
            (today + self._get_default_report_span())
            .astimezone(UTC)
            .replace(tzinfo=None)
            if default_start
            else date_start + self._get_default_report_span()
        )
        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            if date_stop < date_start:
                dbg.logic.debug(
                    "[report] date_stop %s before date_start %s: span reset",
                    date_stop,
                    date_start,
                )
                date_stop = default_stop
        else:
            date_stop = default_stop

        return date_start, date_stop

    def _get_default_report_span(self):
        return timedelta(days=1, microseconds=-1)

    def _get_domain_orders(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        **kwargs,
    ):
        domain = Domain("state", "in", ["paid", "done"])

        if session_ids:
            return domain & Domain("session_id", "in", session_ids)

        date_start, date_stop = self._get_date_start_and_date_stop(
            date_start, date_stop
        )
        domain &= Domain("date_order", ">=", date_start)
        domain &= Domain("date_order", "<=", date_stop)

        if config_ids:
            domain &= Domain("config_id", "in", config_ids)

        return domain

    def _get_report_scope(self, config_ids, session_ids, date_start, date_stop):
        if session_ids:
            sessions = self.env["pos.session"].browse(session_ids).exists()
            sessions.check_access("read")
            configs = sessions.config_id
            configs.check_access("read")
            return configs, sessions
        domain = Domain("start_at", "<=", date_stop) & (
            Domain("stop_at", "=", False) | Domain("stop_at", ">=", date_start)
        )
        domain |= Domain(
            "order_ids",
            "any",
            self._get_domain_orders(date_start, date_stop, config_ids),
        )
        if config_ids:
            domain &= Domain("config_id", "in", config_ids)
        sessions = self.env["pos.session"].search(domain)

        configs = (
            self.env["pos.config"].browse(config_ids).exists()
            if config_ids
            else sessions.config_id
        )
        configs.check_access("read")
        return configs, sessions

    def _get_report_currency(self, configs):
        currencies = configs.currency_id
        if len(currencies) != 1:
            dbg.logic.debug(
                "[report] %d config currencies: company currency used",
                len(currencies),
            )
        return currencies if len(currencies) == 1 else self.env.company.currency_id

    def _get_sales_totals(self, orders, report_currency):
        total = 0.0
        sold = self._prepare_sales_accumulator()
        refunded = self._prepare_sales_accumulator()
        discounted_orders = set()
        discount_amount = 0.0
        precision = self.env["decimal.precision"].get_precision("Product Unit")

        for order in orders.with_context(active_test=False):
            total += self._convert_order_amount(
                order.amount_total, order, report_currency
            )

            session_currency = order.session_id.currency_id
            for line in order.lines:
                accumulator = refunded if line.order_id.is_refund else sold
                self._update_products_and_taxes(
                    line, accumulator, session_currency, precision, report_currency
                )
                if line.discount > 0:
                    discounted_orders.add(order.id)
                    discount_amount += self._convert_order_amount(
                        line._get_discount_amount(), order, report_currency
                    )

        dbg.logic.debug(
            "[report] totals: total=%s sold categories=%d refunded categories=%d"
            " discounted orders=%d discount=%s",
            total,
            len(sold["products"]),
            len(refunded["products"]),
            len(discounted_orders),
            discount_amount,
        )
        return {
            "total": total,
            "sold": sold,
            "refunded": refunded,
            "discount_number": len(discounted_orders),
            "discount_amount": discount_amount,
        }

    def _convert_order_amount(self, amount, order, currency, round=True):
        if order.currency_id == currency:
            return amount
        return order.currency_id._convert(
            amount,
            currency,
            order.company_id,
            order.date_order or fields.Date.today(),
            round=round,
        )

    def _prepare_sales_accumulator(self):
        return {"products": {}, "base_amount": 0.0, "taxes": {}}

    def _get_line_quantity(self, line):
        return line.qty * (-1 if line.order_id.is_refund else 1)

    def _get_product_total_amount(self, line):
        return line.currency_id.round(
            line.price_unit
            * self._get_line_quantity(line)
            * (100 - line.discount)
            / 100.0
        )

    def _update_products_and_taxes(
        self, line, accumulator, currency, precision, report_currency=None
    ):
        report_currency = report_currency or currency

        def convert(amount, round=True):
            return self._convert_order_amount(
                amount, line.order_id, report_currency, round=round
            )

        category = line.product_id.product_tmpl_id.pos_categ_ids[:1]
        combo_products_label = (
            " (" + ", ".join(line.combo_line_ids.product_id.mapped("name")) + ")"
            if line.combo_line_ids
            else ""
        )
        key = (
            line.product_id,
            convert(line.price_unit, round=False),
            line.discount,
            combo_products_label,
        )

        quantity = self._get_line_quantity(line)
        total_amount = convert(self._get_product_total_amount(line))
        taxes = accumulator["taxes"]
        if line.tax_ids_after_fiscal_position:
            line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(
                line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                currency,
                quantity,
                product=line.product_id,
                partner=line.order_id.partner_id or False,
            )
            base_amount = convert(line_taxes["total_excluded"])
            base_by_tax = {}
            for tax in line_taxes["taxes"]:
                taxes.setdefault(
                    tax["id"],
                    {
                        "id": tax["id"],
                        "name": tax["name"],
                        "tax_amount": 0.0,
                        "base_amount": 0.0,
                    },
                )
                taxes[tax["id"]]["tax_amount"] += convert(tax["amount"])
                base_by_tax[tax["id"]] = tax["base"]

            for tax_id, tax_base in base_by_tax.items():
                taxes[tax_id]["base_amount"] += convert(currency.round(tax_base))
        else:
            base_amount = total_amount
            taxes.setdefault(
                0,
                {"id": 0, "name": _("No Taxes"), "tax_amount": 0.0, "base_amount": 0.0},
            )
            taxes[0]["base_amount"] += base_amount

        products = accumulator["products"].setdefault(category, {})
        row = products.setdefault(key, [0.0, 0.0, 0.0])
        row[0] = round(row[0] + quantity, precision)
        row[1] += total_amount
        row[2] += base_amount
        accumulator["base_amount"] += base_amount

    def _prepare_products_section(self, configs, sold, refunded):
        report = self.with_context(
            report_currency_id=self._get_report_currency(configs).id,
        )
        products, products_info = report._get_total_and_qty_per_category(
            self._serialize_products_by_category(sold["products"])
        )
        refund_products, refund_info = report._get_total_and_qty_per_category(
            self._serialize_products_by_category(refunded["products"])
        )
        return {
            "products": products,
            "products_info": products_info,
            "refund_products": refund_products,
            "refund_info": refund_info,
            "taxes": list(sold["taxes"].values()),
            "taxes_info": self._get_taxes_info(sold),
            "refund_taxes": list(refunded["taxes"].values()),
            "refund_taxes_info": self._get_taxes_info(refunded),
        }

    def _get_taxes_info(self, accumulator):
        return {
            "tax_amount": sum(
                tax["tax_amount"] for tax in accumulator["taxes"].values()
            ),
            "base_amount": accumulator["base_amount"],
        }

    def _serialize_products_by_category(self, products_by_category):
        rows = [
            (
                category.name if category else _("Not Categorized"),
                category.id or 0,
                sorted(
                    [
                        {
                            "product_id": product.id,
                            "product_name": product.display_name,
                            "barcode": product.barcode,
                            "quantity": qty,
                            "price_unit": price_unit,
                            "discount": discount,
                            "uom": product.uom_id.name,
                            "total_paid": product_total,
                            "base_amount": base_amount,
                            "combo_products_label": combo_products_label,
                        }
                        for (
                            product,
                            price_unit,
                            discount,
                            combo_products_label,
                        ), (qty, product_total, base_amount) in product_list.items()
                    ],
                    key=lambda line: line["product_name"],
                ),
            )
            for category, product_list in products_by_category.items()
        ]
        rows.sort(key=lambda row: (row[0], row[1]))
        return [{"name": name, "products": products} for name, _id, products in rows]

    def _get_total_and_qty_per_category(self, categories):
        qty_precision = self.env["decimal.precision"].get_precision("Product Unit")
        currency = (
            self.env["res.currency"].browse(self.env.context.get("report_currency_id"))
            or self.env.company.currency_id
        )
        for category_dict in categories:
            category_dict["qty"] = round(
                sum(product["quantity"] for product in category_dict["products"]),
                qty_precision,
            )
            category_dict["total"] = currency.round(
                sum(product["base_amount"] for product in category_dict["products"]),
            )
        all_products = [
            product for category in categories for product in category["products"]
        ]
        return categories, {
            "total": currency.round(
                sum(product["base_amount"] for product in all_products),
            ),
            "qty": round(
                sum(product["quantity"] for product in all_products), qty_precision
            ),
        }

    def _get_counted_payments(self, orders, sessions):
        payments = self._get_payment_totals(orders)
        sessions.check_access("read")
        accounting_report = self.sudo()
        sessions = accounting_report._get_complete_sessions(orders, sessions.sudo())
        return accounting_report._prepare_counted_payments(payments, sessions)

    def _prepare_counted_payments(self, payments, sessions):
        payments_by_session = {}
        for payment in payments:
            payments_by_session.setdefault(payment["session"], []).append(payment)

        account_payments_by_session = (
            self.env["account.payment"]
            .search([("pos_session_id", "in", sessions.ids)])
            .grouped(lambda p: p.pos_session_id.id)
        )
        statement_lines_by_session = (
            self.env["account.bank.statement.line"]
            .search([("pos_session_id", "in", sessions.ids)])
            .grouped(lambda line: line.pos_session_id.id)
        )
        diff_moves = self._get_closing_difference_moves(sessions, payments)
        payment_keys = {(payment["session"], payment["id"]) for payment in payments}
        for (session_id, method_id), move in diff_moves.items():
            if move and (session_id, method_id) not in payment_keys:
                payments_by_session.setdefault(session_id, []).append(
                    self._prepare_payment_row(
                        self.env["pos.payment.method"].browse(method_id),
                        sessions.browse(session_id),
                        0,
                    )
                )

        counted = []
        for session in sessions:
            session_payments = payments_by_session.pop(session.id, [])
            if session.cash_journal_id and not any(
                payment["cash"] and payment["journal_id"] == session.cash_journal_id.id
                for payment in session_payments
            ):
                counted.append(
                    self._prepare_uncounted_cash_row(
                        session,
                        statement_lines_by_session,
                    )
                )
            for payment in session_payments:
                if payment["cash"]:
                    self._count_cash_payment(
                        payment, session, statement_lines_by_session
                    )
                else:
                    self._count_non_cash_payment(
                        payment,
                        diff_moves.get(
                            (session.id, payment["id"]), self.env["account.move"]
                        ),
                        account_payments_by_session.get(
                            session.id, self.env["account.payment"]
                        ),
                    )
            counted += session_payments

        dbg.logic.debug(
            "[report] payments: %d counted rows, %d uncounted sessions, %d diff moves",
            len(counted),
            len(payments_by_session),
            len(diff_moves),
        )
        for orphan_payments in payments_by_session.values():
            counted += orphan_payments
        return counted

    def _get_complete_sessions(self, orders, sessions):
        groups = self.env["pos.order"]._read_group(
            self._get_domain_orders(session_ids=sessions.ids)
            if sessions
            else Domain.FALSE,
            ["session_id"],
            ["__count"],
        )
        captured_counts = {session.id: count for session, count in groups}
        selected = orders.grouped("session_id")
        complete = sessions.filtered(
            lambda session: (
                len(selected.get(session, ())) == captured_counts.get(session.id, 0)
            )
        )
        dbg.logic.debug(
            "[report] drawer scope: %d complete sessions, %d partial sessions omitted",
            len(complete),
            len(sessions - complete),
        )
        return complete

    def _get_payment_totals(self, orders):
        groups = self.env["pos.payment"]._read_group(
            [("pos_order_id", "in", orders.ids)],
            ["payment_method_id", "session_id"],
            ["amount:sum"],
        )
        payments = list(starmap(self._prepare_payment_row, groups))
        payments.sort(key=lambda payment: (payment["id"], payment["session"]))
        return payments

    def _prepare_payment_row(self, method, session, total):
        return {
            "id": method.id,
            "session": session.id,
            "name": method.name,
            "cash": method.is_cash_count,
            "total": total,
            "journal_id": method.journal_id.id,
            "count": False,
        }

    def _get_closing_difference_moves(self, sessions, payments):
        if not sessions:
            return {}
        sessions_by_id = {session.id: session for session in sessions}
        methods = self.env["pos.payment.method"].browse(
            sorted({payment["id"] for payment in payments if not payment["cash"]})
        )
        ref_by_key = {
            (payment["session"], payment["id"]): sessions_by_id[
                payment["session"]
            ]._get_diff_account_move_ref(methods.browse(payment["id"]))
            for payment in payments
            if not payment["cash"] and payment["session"] in sessions_by_id
        }
        moves = self.env["account.move"].search(
            Domain("state", "=", "posted")
            & (
                Domain("pos_diff_session_id", "in", sessions.ids)
                | Domain(
                    [
                        ("pos_diff_payment_method_id", "=", False),
                        ("ref", "in", list(set(ref_by_key.values()))),
                        ("journal_id", "in", methods.journal_id.ids),
                    ]
                )
            )
        )
        move_by_key = {
            (move.pos_diff_session_id.id, move.pos_diff_payment_method_id.id): move
            for move in moves
            if move.pos_diff_session_id and move.pos_diff_payment_method_id
        }
        legacy_candidates = {}
        ambiguous = set()
        for move in moves.filtered(lambda move: not move.pos_diff_payment_method_id):
            keys = self._get_legacy_difference_keys(move, methods, ref_by_key)
            if len(keys) != 1:
                ambiguous.update(keys)
                continue
            key = next(iter(keys))
            legacy_candidates.setdefault(key, []).append(move)
        for key in ambiguous | legacy_candidates.keys():
            if key not in move_by_key:
                candidates = legacy_candidates.get(key, [])
                move_by_key[key] = (
                    candidates[0]
                    if key not in ambiguous and len(candidates) == 1
                    else None
                )
        dbg.logic.debug(
            "[report] closing differences: %d resolved, %d ambiguous",
            sum(move is not None for move in move_by_key.values()),
            sum(move is None for move in move_by_key.values()),
        )
        return move_by_key

    def _get_legacy_difference_keys(self, move, methods, ref_by_key):
        """Resolve old linked entries by accounting identity before mutable labels."""
        if not move.pos_diff_session_id:
            return {
                key
                for key, ref in ref_by_key.items()
                if ref == move.ref
                and methods.browse(key[1]).journal_id == move.journal_id
            }
        session = move.pos_diff_session_id
        candidates = (methods | session.payment_method_ids).filtered(
            lambda method: (
                method.split_transactions
                and method.type == "bank"
                and method.journal_id == move.journal_id
                and method.outstanding_account_id in move.line_ids.account_id
            )
        )
        exact = candidates.filtered(
            lambda method: ref_by_key.get((session.id, method.id)) == move.ref
        )
        return {(session.id, method.id) for method in exact or candidates}

    def _get_session_cash_moves(self, session, statement_lines_by_session):
        """Exclude closing entries using purpose tags or legacy reconciliation."""
        moves = (
            statement_lines_by_session.get(
                session.id, self.env["account.bank.statement.line"]
            )
            .filtered(
                lambda line: line.pos_cash_move_type not in ("payment", "difference")
            )
            .sorted(lambda line: (line.date, line.id))
        )
        legacy = moves.filtered(lambda line: not line.pos_cash_move_type)
        if session.state == "closed" and session.move_id and legacy:
            lines = legacy.move_id.line_ids
            partials = lines.matched_debit_ids | lines.matched_credit_ids
            settlement_moves = self.env["account.move"]
            for partial in partials:
                if partial.debit_move_id.move_id == session.move_id:
                    settlement_moves |= partial.credit_move_id.move_id
                if partial.credit_move_id.move_id == session.move_id:
                    settlement_moves |= partial.debit_move_id.move_id
            moves = moves.filtered(lambda line: line.move_id not in settlement_moves)
            dbg.logic.debug(
                "[report] legacy cash session=%s: excluded %d reconciled settlement moves",
                session.id,
                len(settlement_moves),
            )
        if session.state == "closed" and legacy:
            moves = self._get_cash_moves_without_legacy_difference(session, moves)
        return moves

    def _get_cash_moves_without_legacy_difference(self, session, moves):
        """Exclude only a uniquely identifiable old counting adjustment."""
        difference = (
            session.cash_register_balance_end_real - session.cash_register_balance_end
        )
        if session.currency_id.is_zero(difference):
            return moves
        residual = sum(moves.mapped("amount")) - session.cash_real_transaction
        if session.currency_id.compare_amounts(residual, difference) != 0:
            return moves
        diff_accounts = (
            session.cash_journal_id.loss_account_id
            | session.cash_journal_id.profit_account_id
        )
        candidates = moves.filtered(
            lambda line: (
                not line.pos_cash_move_type
                and line.move_id.line_ids.account_id & diff_accounts
                and session.currency_id.compare_amounts(line.amount, difference) == 0
            )
        )
        if len(candidates) == 1:
            return moves - candidates
        dbg.logic.debug(
            "[report] legacy drawer %s: %d candidate counting adjustments",
            session.id,
            len(candidates),
        )
        return moves

    def _prepare_uncounted_cash_row(self, session, statement_lines_by_session):
        payment = {
            "id": False,
            "session": session.id,
            "name": _("Cash %(session_name)s", session_name=session.name),
            "cash": True,
            "journal_id": session.cash_journal_id.id,
            "total": 0,
        }
        self._count_cash_payment(payment, session, statement_lines_by_session)
        return payment

    def _count_cash_payment(self, payment, session, statement_lines_by_session):
        if payment["journal_id"] != session.cash_journal_id.id:
            dbg.logic.debug(
                "[report] session %s: no stored drawer count for cash method %s",
                session.id,
                payment["id"],
            )
            return
        cash_moves = self._get_session_cash_moves(session, statement_lines_by_session)
        cash_transactions = (
            session.cash_real_transaction
            if session.state == "closed"
            else sum(cash_moves.mapped("amount"))
        )
        payment["final_count"] = (
            payment["total"] + session.cash_register_balance_start + cash_transactions
        )
        payment["money_counted"] = session.cash_register_balance_end_real or 0
        payment["money_difference"] = payment["money_counted"] - payment["final_count"]

        payment["cash_moves"] = self._prepare_cash_movement_rows(session, cash_moves)
        payment["count"] = True

    def _prepare_cash_movement_rows(self, session, cash_moves):
        cash_in_out_list = []
        if not session.currency_id.is_zero(session.cash_register_balance_start):
            cash_in_out_list.append(
                {
                    "name": _("Cash Opening"),
                    "amount": session.cash_register_balance_start,
                }
            )
        legacy = cash_moves.filtered(lambda line: not line.pos_cash_move_type)
        if (
            session.state == "closed"
            and legacy
            and session.currency_id.compare_amounts(
                sum(cash_moves.mapped("amount")), session.cash_real_transaction
            )
            != 0
        ):
            cash_moves -= legacy
            legacy_amount = session.cash_real_transaction - sum(
                cash_moves.mapped("amount")
            )
            if not session.currency_id.is_zero(legacy_amount):
                cash_in_out_list.append(
                    {"name": _("Other cash movements"), "amount": legacy_amount}
                )
            dbg.logic.debug(
                "[report] session %s: summarized %d legacy cash entries as %s",
                session.id,
                len(legacy),
                legacy_amount,
            )
        cash_in_count = cash_out_count = 0
        for cash_move in cash_moves:
            if cash_move.move_id.journal_id != session.cash_journal_id:
                continue
            if cash_move.amount > 0:
                cash_in_count += 1
                name = _("Cash in %(number)s", number=cash_in_count)
            else:
                cash_out_count += 1
                name = _("Cash out %(number)s", number=cash_out_count)
            cash_in_out_list.append(
                {"name": cash_move.payment_ref or name, "amount": cash_move.amount}
            )
        return cash_in_out_list

    def _count_non_cash_payment(self, payment, diff_move, account_payments):
        if diff_move is None:
            dbg.logic.debug(
                "[report] method %s session %s: ambiguous legacy difference; count omitted",
                payment["id"],
                payment["session"],
            )
            return
        session = self.env["pos.session"].browse(payment["session"])
        if diff_move:
            method = self.env["pos.payment.method"].browse(payment["id"])
            source_lines = diff_move.line_ids.filtered(
                lambda line: line.account_id == method.outstanding_account_id
            )
            sign = 1
            if not source_lines:
                accounts = (
                    method.journal_id.loss_account_id
                    | method.journal_id.profit_account_id
                )
                source_lines = diff_move.line_ids.filtered(
                    lambda line: line.account_id in accounts
                )
                sign = -1
            if not source_lines:
                dbg.logic.debug(
                    "[report] difference move %s has no identifiable source or counterpart; count omitted",
                    diff_move.id,
                )
                return
            difference = sign * sum(
                line.currency_id._convert(
                    line.amount_currency,
                    session.currency_id,
                    session.company_id,
                    diff_move.date,
                )
                for line in source_lines
            )
            dbg.logic.debug(
                "[report] difference move %s: signed lines %s -> %s %s",
                diff_move.id,
                source_lines.ids,
                difference,
                session.currency_id.name,
            )
            payment["final_count"] = payment["total"]
            payment["money_difference"] = difference
            payment["money_counted"] = payment["total"] + difference
            payment["cash_moves"] = self._prepare_counting_difference_moves(
                difference, difference < 0
            )
            payment["count"] = True
            return

        settled_by = account_payments.filtered(
            lambda p, method_id=payment["id"]: p.pos_payment_method_id.id == method_id
        )
        if not settled_by:
            dbg.logic.debug(
                "[report] method %s in session %s: no diff move, no account.payment",
                payment["id"],
                payment["session"],
            )
            return
        payment["final_count"] = payment["total"]
        payment["money_counted"] = sum(
            settled.currency_id._convert(
                settled.amount_signed,
                session.currency_id,
                session.company_id,
                settled.date,
            )
            for settled in settled_by
        )
        payment["money_difference"] = payment["money_counted"] - payment["final_count"]
        payment["cash_moves"] = self._prepare_counting_difference_moves(
            payment["money_difference"], payment["money_difference"] < 0
        )
        payment["count"] = True

    def _prepare_counting_difference_moves(self, difference, is_loss):
        if not difference:
            return []
        move_name = (
            _("Difference observed during the counting (Loss)")
            if is_loss
            else _("Difference observed during the counting (Profit)")
        )
        return [{"name": move_name, "amount": difference}]

    def _prepare_payments_section(self, payments, session_ids):
        payments_per_method = {}
        for payment in payments:
            if not payment["id"]:
                continue
            method_name = payment["name"]
            payment["name"] = (
                method_name
                + " "
                + self.env["pos.session"].browse(payment["session"]).name
            )
            per_method = payments_per_method.setdefault(
                payment["id"], {"name": method_name, "total": 0.0}
            )
            per_method["total"] += payment["total"]

        return {
            "payments": payments,
            "payments_per_method": list(payments_per_method.values()),
            "show_payment_per_method": not session_ids,
            "total_paid": sum(payment["total"] for payment in payments),
        }

    def _update_payment_rows_with_report_currency(
        self, payments, orders, sessions, currency
    ):
        totals = {}
        foreign_orders = orders.filtered(lambda order: order.currency_id != currency)
        for payment in foreign_orders.payment_ids:
            key = (payment.session_id.id, payment.payment_method_id.id)
            totals[key] = totals.get(key, 0.0) + self._convert_order_amount(
                payment.amount, payment.pos_order_id, currency
            )
        sessions_by_id = {
            session.id: session for session in sessions | orders.session_id
        }
        for row in payments:
            session = sessions_by_id[row["session"]]
            date = session.stop_at or session.start_at or fields.Date.today()

            def convert(amount, session=session, date=date):
                if session.currency_id == currency:
                    return amount
                return session.currency_id._convert(
                    amount, currency, session.company_id, date
                )

            converted_total = convert(row["total"])
            row["total"] = totals.get((session.id, row["id"]), converted_total)
            for key in ("final_count", "money_counted", "money_difference"):
                if key in row:
                    row[key] = convert(row[key])
            for movement in row.get("cash_moves", []):
                movement["amount"] = convert(movement["amount"])
            if row.get("count"):
                row["money_difference"] = row["money_counted"] - row["final_count"]

    def _prepare_invoice_section(self, orders, currency):
        """List invoices from the same order selection as sales and payments."""
        invoice_list = []
        invoice_total = 0.0
        for session, invoiced_orders in (
            orders.filtered("is_invoiced").grouped("session_id").items()
        ):
            invoices = []
            for order in invoiced_orders:
                move = order.account_move
                total = move.currency_id._convert(
                    move.amount_total_in_currency_signed,
                    currency,
                    move.company_id,
                    move.date,
                )
                invoices.append(
                    {
                        "total": total,
                        "name": move.name,
                        "order_ref": order.pos_reference,
                    }
                )
                invoice_total += total
            invoice_list.append({"name": session.name, "invoices": invoices})
        return {"invoice_list": invoice_list, "invoice_total": invoice_total}
