from datetime import UTC, timedelta

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

        return {
            "state": sessions.state if len(sessions) == 1 else "multiple",
            "date_start": sessions.start_at if len(sessions) == 1 else date_start,
            "date_stop": sessions.stop_at if len(sessions) == 1 else date_stop,
            "session_name": sessions.name if len(sessions) == 1 else False,
            "opening_note": sessions.opening_notes if len(sessions) == 1 else False,
            "closing_note": sessions.closing_notes if len(sessions) == 1 else False,
            "config_names": configs.mapped("name"),
            "company_name": self.env.company.name,
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
            **self._prepare_invoice_section(sessions, currency),
        }

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
        else:
            domain = Domain("start_at", "<=", date_stop) & (
                Domain("stop_at", "=", False) | Domain("stop_at", ">=", date_start)
            )
            if config_ids:
                domain &= Domain("config_id", "in", config_ids)
            sessions = self.env["pos.session"].search(domain)

        configs = (
            self.env["pos.config"].browse(config_ids).exists()
            if config_ids
            else sessions.config_id
        )
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

        for order in orders:
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
                    {"name": tax["name"], "tax_amount": 0.0, "base_amount": 0.0},
                )
                taxes[tax["id"]]["tax_amount"] += convert(tax["amount"])
                base_by_tax[tax["id"]] = tax["base"]

            for tax_id, tax_base in base_by_tax.items():
                taxes[tax_id]["base_amount"] += convert(currency.round(tax_base))
        else:
            base_amount = total_amount
            taxes.setdefault(
                0, {"name": _("No Taxes"), "tax_amount": 0.0, "base_amount": 0.0}
            )
            taxes[0]["base_amount"] += base_amount

        products = accumulator["products"].setdefault(category, {})
        row = products.setdefault(key, [0.0, 0.0, 0.0])
        row[0] = round(row[0] + quantity, precision)
        row[1] += total_amount
        row[2] += base_amount
        accumulator["base_amount"] += base_amount

    def _prepare_products_section(self, configs, sold, refunded):
        report = self.with_context(config_id=configs[0].id if configs else False)
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
        price_precision = self.env["decimal.precision"].get_precision("Product Price")
        for category_dict in categories:
            category_dict["qty"] = round(
                sum(product["quantity"] for product in category_dict["products"]),
                qty_precision,
            )
            category_dict["total"] = round(
                sum(product["base_amount"] for product in category_dict["products"]),
                price_precision,
            )
        all_products = [
            product for category in categories for product in category["products"]
        ]
        return categories, {
            "total": round(
                sum(product["base_amount"] for product in all_products),
                price_precision,
            ),
            "qty": round(
                sum(product["quantity"] for product in all_products), qty_precision
            ),
        }

    def _get_counted_payments(self, orders, sessions):
        payments = self._get_payment_totals(orders)
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
        previous_sessions = self._get_previous_closed_sessions(sessions)

        counted = []
        for session in sessions:
            session_payments = payments_by_session.pop(session.id, [])
            if not any(payment["cash"] for payment in session_payments):
                counted.append(
                    self._prepare_uncounted_cash_row(
                        session,
                        statement_lines_by_session,
                        previous_sessions.get(session.id, self.env["pos.session"]),
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
            "[report] payments: %d counted rows, %d orphan sessions, %d diff moves",
            len(counted),
            len(payments_by_session),
            len(diff_moves),
        )
        for orphan_payments in payments_by_session.values():
            counted += orphan_payments
        return counted

    def _get_payment_totals(self, orders):
        groups = self.env["pos.payment"]._read_group(
            [("pos_order_id", "in", orders.ids)],
            ["payment_method_id", "session_id"],
            ["amount:sum"],
        )
        payments = [
            {
                "id": method.id,
                "session": session.id,
                "name": method.name,
                "cash": method.is_cash_count,
                "total": total,
                "journal_id": method.journal_id.id,
                "count": False,
            }
            for method, session, total in groups
        ]
        payments.sort(key=lambda payment: (payment["id"], payment["session"]))
        return payments

    def _get_closing_difference_moves(self, sessions, payments):
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
        if not ref_by_key:
            return {}

        moves = self.env["account.move"].search(
            [
                ("ref", "in", list(set(ref_by_key.values()))),
                ("journal_id", "in", methods.journal_id.ids),
            ]
        )
        move_by_key = {}
        journal_by_method = {method.id: method.journal_id.id for method in methods}
        moves_by_ref_and_journal = {}
        for move in moves:
            moves_by_ref_and_journal.setdefault((move.ref, move.journal_id.id), move)
        for key, ref in ref_by_key.items():
            journal_id = journal_by_method.get(key[1])
            match = moves_by_ref_and_journal.get((ref, journal_id))
            if match is not None:
                move_by_key[key] = match
        return move_by_key

    def _get_session_cash_moves(self, session, statement_lines_by_session):
        return statement_lines_by_session.get(
            session.id, self.env["account.bank.statement.line"]
        ).sorted(lambda line: (line.date, line.id))

    def _get_previous_closed_sessions(self, sessions):
        if not sessions:
            return {}
        candidates = self.env["pos.session"].search(
            [
                ("config_id", "in", sessions.config_id.ids),
                ("state", "=", "closed"),
                ("id", "<", max(sessions.ids)),
            ],
            order="id desc",
        )
        by_config = candidates.grouped(lambda session: session.config_id.id)
        return {
            session.id: next(
                (
                    candidate
                    for candidate in by_config.get(session.config_id.id, ())
                    if candidate.id < session.id
                ),
                self.env["pos.session"],
            )
            for session in sessions
        }

    def _prepare_uncounted_cash_row(
        self, session, statement_lines_by_session, previous_session
    ):
        final_count = (
            previous_session.cash_register_balance_end_real
            + session.cash_real_transaction
        )
        cash_moves = self._get_session_cash_moves(session, statement_lines_by_session)

        diff_accounts = (
            session.cash_journal_id.loss_account_id
            | session.cash_journal_id.profit_account_id
        )
        if diff_accounts:
            cash_moves = cash_moves.filtered(
                lambda line, accounts=diff_accounts: (
                    not (line.move_id.line_ids.account_id & accounts)
                )
            )

        cash_in_out_list = []
        if previous_session.cash_register_balance_end_real > 0:
            cash_in_out_list.append(
                {
                    "name": _("Cash Opening"),
                    "amount": previous_session.cash_register_balance_end_real,
                }
            )
        cash_in_out_list += [
            {"name": cash_move.payment_ref, "amount": cash_move.amount}
            for cash_move in cash_moves
        ]

        return {
            "id": False,
            "session": session.id,
            "name": _("Cash %(session_name)s", session_name=session.name),
            "cash": True,
            "journal_id": session.cash_journal_id.id,
            "total": 0,
            "final_count": final_count,
            "money_counted": session.cash_register_balance_end_real,
            "money_difference": session.cash_register_balance_end_real - final_count,
            "cash_moves": cash_in_out_list,
            "count": True,
        }

    def _count_cash_payment(self, payment, session, statement_lines_by_session):
        payment["final_count"] = (
            payment["total"]
            + session.cash_register_balance_start
            + session.cash_real_transaction
        )
        payment["money_counted"] = session.cash_register_balance_end_real or 0
        payment["money_difference"] = payment["money_counted"] - payment["final_count"]

        cash_in_out_list = []
        if session.cash_register_balance_start > 0:
            cash_in_out_list.append(
                {
                    "name": _("Cash Opening"),
                    "amount": session.cash_register_balance_start,
                }
            )
        cash_in_count = cash_out_count = 0
        for cash_move in self._get_session_cash_moves(
            session, statement_lines_by_session
        ):
            if cash_move.move_id.journal_id.id != payment["journal_id"]:
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
        payment["cash_moves"] = cash_in_out_list
        payment["count"] = True

    def _count_non_cash_payment(self, payment, diff_move, account_payments):
        session = self.env["pos.session"].browse(payment["session"])
        journal = self.env["pos.payment.method"].browse(payment["id"]).journal_id
        diff_accounts = diff_move.line_ids.account_id
        is_loss = bool(journal.loss_account_id & diff_accounts)
        is_profit = bool(journal.profit_account_id & diff_accounts)

        if is_loss or is_profit:
            payment["final_count"] = payment["total"]
            payment["money_difference"] = diff_move.company_currency_id._convert(
                -diff_move.amount_total if is_loss else diff_move.amount_total,
                session.currency_id,
                session.company_id,
                diff_move.date,
            )
            payment["money_counted"] = (
                payment["final_count"] + payment["money_difference"]
            )
            payment["cash_moves"] = self._prepare_counting_difference_moves(
                payment["money_difference"], is_loss
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
        """Count in the session currency, then present every amount in report currency.

        Sales payments use their order date, like sales totals. Cash counts use
        the closing date (or opening date while open). Counting differences
        stay independent of exchange-rate changes between sales and closing.
        """
        totals = {}
        for payment in orders.payment_ids:
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

    def _prepare_invoice_section(self, sessions, currency=None):
        currency = currency or self._get_report_currency(sessions.config_id)
        invoice_list = []
        invoice_total = 0.0
        for session in sessions:
            invoices = []
            for order in session._get_invoiced_orders():
                move = order.account_move
                total = move.company_currency_id._convert(
                    move.amount_total_signed, currency, move.company_id, move.date
                )
                invoices.append(
                    {
                        "total": total,
                        "name": move.name,
                        "order_ref": order.pos_reference,
                    }
                )
                invoice_total += self._convert_order_amount(
                    order.amount_paid, order, currency
                )
            invoice_list.append({"name": session.name, "invoices": invoices})
        return {"invoice_list": invoice_list, "invoice_total": invoice_total}
