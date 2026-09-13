import logging
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import new_test_user, tagged
from odoo.tools import SQL

from odoo.addons.point_of_sale.models.pos_config import (
    DEFAULT_LIMIT_LOAD_PARTNER,
    DEFAULT_LIMIT_LOAD_PRODUCT,
)
from odoo.addons.point_of_sale.tests.common import CommonPosTest

log = logging.getLogger("odoo.addons.point_of_sale.debug.challenge")
log.setLevel(logging.DEBUG)


@tagged("post_install", "-at_install")
class TestPosModelRegressions(CommonPosTest):
    def test_pos_address_cache_is_language_sensitive(self):
        self.env["res.lang"]._activate_lang("es_MX")
        country = self.env.ref("base.aq")
        country.with_context(lang="en_US").name = "Antarctica"
        country.with_context(lang="es_MX").name = "Antártida"
        partner = self.env["res.partner"].create(
            {"name": "Translated address", "country_id": country.id}
        )
        english = partner.with_context(lang="en_US")
        spanish = partner.with_context(lang="es_MX")
        self.assertIn("Antarctica", english.pos_contact_address)
        self.assertIn("Antártida", spanish.pos_contact_address)
        country.with_context(lang="es_MX").name = "Antártida editada"
        self.assertIn("Antártida editada", spanish.pos_contact_address)
        self.assertIn("Antarctica", english.pos_contact_address)
        log.debug(
            "CHALLENGE address en=%r es=%r",
            english.pos_contact_address,
            spanish.pos_contact_address,
        )

    def test_address_edits_refresh_unchanged_partner_in_delta(self):
        self._assert_address_edits_refresh_partner(with_country=True)

    def test_address_edits_refresh_state_only_partner_in_delta(self):
        self._assert_address_edits_refresh_partner(with_country=False)

    def _assert_address_edits_refresh_partner(self, *, with_country):
        session = self._session()
        country = self.env.ref("base.aq")
        country.address_format = "%(state_name)s\n%(country_name)s"
        state = self.env["res.country.state"].create(
            {"name": "Original state", "code": "AS", "country_id": country.id}
        )
        partner = self.env["res.partner"].create(
            {
                "name": "AAA Address delta",
                "country_id": country.id if with_country else False,
                "state_id": state.id,
            }
        )
        initial = session.load_data([])
        self.assertIn(partner.id, {row["id"] for row in initial["res.partner"]})
        cutoff = self.env.cr.now() + timedelta(hours=1)
        partner_date = partner.write_date
        incremental = session.with_context(
            pos_last_server_date=fields.Datetime.to_string(cutoff),
            pos_limited_loading=True,
        )
        unchanged = incremental.load_data([])
        self.assertNotIn(partner.id, {row["id"] for row in unchanged["res.partner"]})
        for record in (country, state):
            with self.subTest(model=record._name), self.env.cr.savepoint():
                record.name = "Edited address label"
                self._stamp(record, cutoff + timedelta(seconds=1))
                self.assertEqual(partner.write_date, partner_date)
                delta = incremental.load_data([])
                rows = {row["id"]: row for row in delta[record._name]}
                log.debug(
                    "CHALLENGE edited=%s id=%s delta=%s", record._name, record.id, rows
                )
                self.assertIn(record.id, rows)
                self.assertEqual(rows[record.id]["name"], "Edited address label")
                self.assertIn(partner.id, {row["id"] for row in delta["res.partner"]})
                partner_row = next(
                    row for row in delta["res.partner"] if row["id"] == partner.id
                )
                self.assertEqual(
                    partner_row["pos_contact_address"],
                    partner._display_address(without_company=True),
                )
                # Keep the next arm independent of this reference's newer timestamp.
                self._stamp(record, cutoff - timedelta(seconds=1))

    def test_category_reparenting_updates_warm_descendants(self):
        first, second = self.env["pos.category"].create(
            [{"name": "First"}, {"name": "Second"}]
        )
        middle = self.env["pos.category"].create(
            {"name": "Middle", "parent_id": first.id}
        )
        leaf = self.env["pos.category"].create({"name": "Leaf", "parent_id": middle.id})
        self.assertEqual(leaf.display_name, "First / Middle / Leaf")
        middle.parent_id = second
        self.assertEqual(leaf.display_name, "Second / Middle / Leaf")
        first.name = "Detached ancestor"
        self.assertEqual(leaf.display_name, "Second / Middle / Leaf")
        second.name = "New ancestor"
        self.assertEqual(leaf.display_name, "New ancestor / Middle / Leaf")
        middle.parent_id = False
        self.assertEqual(leaf.display_name, "Middle / Leaf")
        log.debug("CHALLENGE reparented warm category=%s", leaf.display_name)

    def test_cashier_can_load_state_only_partner(self):
        cashier = new_test_user(
            self.env,
            login="challenge_state_cashier",
            groups="base.group_user,point_of_sale.group_pos_user",
            company_id=self.company.id,
        )
        country = self.env.ref("base.aq")
        state = self.env["res.country.state"].create(
            {"name": "Cashier state", "code": "CC", "country_id": country.id}
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Cashier state-only customer",
                "state_id": state.id,
                "country_id": False,
            }
        )
        data = (
            self.env["res.partner"]
            .with_user(cashier)
            .get_new_partner(self.pos_config_usd.id, [("id", "=", partner.id)], 0)
        )
        log.debug("CHALLENGE cashier=%s countries=%s", cashier.id, data["res.country"])
        self.assertEqual([row["id"] for row in data["res.partner"]], partner.ids)
        self.assertIn(country.id, {row["id"] for row in data["res.country"]})
        self.assertIn(state.id, {row["id"] for row in data["res.country.state"]})

    def test_loading_limits_outside_postgresql_range(self):
        parameters = self.env["ir.config_parameter"].sudo()
        for name in ("limited_product_count", "limited_customer_count"):
            parameters.set_param(f"point_of_sale.{name}", str(2**63))
        log.debug("CHALLENGE load with limits outside PostgreSQL bigint range")
        data = self._session().load_data([])
        self.assertTrue(data["product.template"])
        self.assertTrue(data["res.partner"])

    def test_negative_loading_limits_fall_back_to_defaults(self):
        parameters = self.env["ir.config_parameter"].sudo()
        for name in ("limited_product_count", "limited_customer_count"):
            parameters.set_param(f"point_of_sale.{name}", "-1")
        log.debug(
            "LOAD negative product and customer limits through complete session load"
        )
        data = self._session().load_data([])
        self.assertTrue(data["product.template"])
        self.assertTrue(data["res.partner"])

    def test_loading_limit_parsing_preserves_zero_and_positive_values(self):
        parameters = self.env["ir.config_parameter"].sudo()
        config = self.pos_config_usd
        for name, getter, default in (
            (
                "limited_product_count",
                config.get_limited_product_count,
                DEFAULT_LIMIT_LOAD_PRODUCT,
            ),
            (
                "limited_customer_count",
                config._get_limited_partner_count,
                DEFAULT_LIMIT_LOAD_PARTNER,
            ),
        ):
            for value in ("0", "7", str(2**63 - 1), "-1", "invalid"):
                with self.subTest(name=name, value=value):
                    parameters.set_param(f"point_of_sale.{name}", value)
                    count = getter()
                    log.debug(
                        "LOAD parameter=%s value=%r parsed=%s", name, value, count
                    )
                    if value in ("invalid", "-1"):
                        self.assertEqual(count, default)
                    else:
                        self.assertEqual(count, int(value))

    def _session(self, config=None):
        config = config or self.pos_config_usd
        if not config.current_session_id:
            config.open_ui()
        return config.current_session_id

    def _order(self, specs, config=None, paid=False):
        session = self._session(config)
        total = sum(spec["qty"] * spec.get("price_unit", 1) for spec in specs)
        order = self.env["pos.order"].create(
            {
                "session_id": session.id,
                "partner_id": self.partner_mobt.id,
                "pricelist_id": session.config_id.pricelist_id.id,
                "amount_total": total,
                "amount_paid": 0,
                "amount_tax": 0,
                "amount_return": 0,
                "lines": [
                    Command.create(
                        {
                            "price_unit": 1,
                            "price_subtotal": spec["qty"] * spec.get("price_unit", 1),
                            "price_subtotal_incl": spec["qty"]
                            * spec.get("price_unit", 1),
                            "tax_ids": [Command.clear()],
                            **spec,
                        }
                    )
                    for spec in specs
                ],
            }
        )
        if paid:
            order._recompute_amounts()
            self.env["pos.payment"].create(
                {
                    "pos_order_id": order.id,
                    "payment_method_id": self.bank_payment_method.id,
                    "amount": order.amount_total,
                }
            )
            order._recompute_amounts()
            order.action_pos_order_paid()
        return order

    def _stamp(self, records, when):
        self.env.flush_all()
        self.env.cr.execute(
            SQL(
                "UPDATE %s SET write_date = %s WHERE id = ANY(%s)",
                SQL.identifier(records._table),
                when,
                records.ids,
            )
        )
        records.invalidate_recordset(["write_date"])
        log.debug(
            "CHALLENGE stamp %s ids=%s dates=%s",
            records._name,
            records.ids,
            records.mapped("write_date"),
        )

    def test_stock_persisted_order_and_single_line_control(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.pos_config_usd.picking_type_id = warehouse.pos_type_id
        warehouse.pos_type_id.use_existing_lots = True
        root = warehouse.lot_stock_id
        bins = self.env["stock.location"].create(
            [
                {
                    "name": name,
                    "location_id": root.id,
                    "company_id": self.env.company.id,
                }
                for name in ["Challenge A", "Challenge B"]
            ]
        )
        for split in [False, True]:
            product = self.env["product.product"].create(
                {
                    "name": f"Challenge lot {split}",
                    "is_storable": True,
                    "tracking": "lot",
                    "available_in_pos": True,
                }
            )
            lot = self.env["stock.lot"].create(
                {
                    "name": f"LOT-{split}",
                    "product_id": product.id,
                    "company_id": self.env.company.id,
                }
            )
            for location in bins:
                self.env["stock.quant"]._update_available_quantity(
                    product, location, 1, lot_id=lot
                )
            quantities = [1, 1] if split else [2]
            order = self._order(
                [
                    {
                        "product_id": product.id,
                        "qty": qty,
                        "price_unit": index + 1,
                        "pack_lot_ids": [Command.create({"lot_name": lot.name})],
                    }
                    for index, qty in enumerate(quantities)
                ]
            )
            order._create_order_picking()
            quants = self.env["stock.quant"].search(
                [("product_id", "=", product.id), ("location_id", "in", bins.ids)]
            )
            balances = sorted(quants.mapped("quantity"))
            log.debug(
                "CHALLENGE stock persisted=%s split=%s states=%s balances=%s",
                order.lines.ids,
                split,
                order.picking_ids.mapped("state"),
                balances,
            )
            self.assertEqual(order.picking_ids.mapped("state"), ["done"])
            self.assertEqual(balances, [0.0, 0.0])

    def test_fiscal_cache_and_normal_company_scope(self):
        a = self.env.company
        b = self.env["res.company"].create({"name": "Challenge company B"})
        positions = self.env["account.fiscal.position"].create(
            [
                {"name": "Challenge A", "company_id": a.id},
                {"name": "Challenge B", "company_id": b.id},
            ]
        )
        partner = self.env["res.partner"].create({"name": "Challenge company partner"})
        partner.with_company(a).property_account_position_id = positions[0]
        partner.with_company(b).property_account_position_id = positions[1]
        partner.invalidate_recordset(["fiscal_position_id"])
        first = partner.with_company(a).fiscal_position_id
        switched = partner.with_company(b).fiscal_position_id
        partner.invalidate_recordset(["fiscal_position_id"])
        fresh = partner.with_company(b).fiscal_position_id
        self.assertEqual(
            (first.id, switched.id, fresh.id),
            (positions[0].id, positions[1].id, positions[1].id),
        )
        partner.invalidate_recordset(["fiscal_position_id"])
        normal = (
            self.env["res.partner"]
            .with_company(a)
            .get_new_partner(self.pos_config_usd.id, [("id", "=", partner.id)], 0)
        )
        self.assertEqual(
            normal["res.partner"][0]["fiscal_position_id"], positions[0].id
        )
        log.debug(
            "CHALLENGE fiscal first=%s switched=%s fresh=%s normal_payload=%s",
            first.id,
            switched.id,
            fresh.id,
            normal["res.partner"][0]["fiscal_position_id"],
        )

    def test_full_session_country_delta_and_full_reload_control(self):
        session = self._session()
        country = self.env.ref("base.aq")
        country_partners = self.env["res.partner"].search(
            [("country_id", "=", country.id)]
        )
        country_partners.country_id = False
        cutoff = self.env.cr.now() + timedelta(hours=1)
        initial = session.load_data([])
        self.assertNotIn(country.id, [row["id"] for row in initial["res.country"]])
        partner = self.env["res.partner"].create(
            {"name": "AAA Challenge Antarctica", "country_id": country.id}
        )
        self._stamp(partner, cutoff + timedelta(seconds=1))
        delta = session.with_context(
            pos_last_server_date=fields.Datetime.to_string(cutoff),
            pos_limited_loading=True,
        ).load_data([])
        full = session.with_context(
            pos_last_server_date=fields.Datetime.to_string(cutoff),
            pos_limited_loading=False,
        ).load_data([])
        self.assertIn(partner.id, [row["id"] for row in delta["res.partner"]])
        self.assertIn(country.id, [row["id"] for row in delta["res.country"]])
        self.assertIn(country.id, [row["id"] for row in full["res.country"]])
        log.debug(
            "CHALLENGE country initial=%s delta_partners=%s delta_countries=%s full_countries=%s cutoff=%s config_change=%s",
            [r["id"] for r in initial["res.country"]],
            [r["id"] for r in delta["res.partner"]],
            [r["id"] for r in delta["res.country"]],
            [r["id"] for r in full["res.country"]],
            cutoff,
            self.pos_config_usd.last_data_change,
        )

    def test_full_session_scheduled_price_and_full_reload_control(self):
        config = self.pos_config_usd
        pricelist = self.env["product.pricelist"].create(
            {"name": "Challenge future prices", "currency_id": config.currency_id.id}
        )
        config.write(
            {
                "use_pricelist": True,
                "pricelist_id": pricelist.id,
                "available_pricelist_ids": [Command.set(pricelist.ids)],
            }
        )
        session = self._session(config)
        cutoff = self.env.cr.now() + timedelta(hours=1)
        starts = cutoff + timedelta(days=1)
        item = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "applied_on": "3_global",
                "compute_price": "fixed",
                "fixed_price": 7,
                "date_start": starts,
            }
        )
        with patch.object(fields.Datetime, "now", return_value=cutoff):
            initial = session.load_data([])
        with patch.object(
            fields.Datetime, "now", return_value=starts + timedelta(hours=1)
        ):
            delta = session.with_context(
                pos_last_server_date=fields.Datetime.to_string(cutoff)
            ).load_data([])
            full = session.with_context(pos_limited_loading=False).load_data([])

        def ids(data):
            return [row["id"] for row in data["product.pricelist.item"]]

        log.debug(
            "CHALLENGE scheduled initial=%s delta=%s full=%s item=%s config_change=%s cutoff=%s",
            ids(initial),
            ids(delta),
            ids(full),
            item.id,
            config.last_data_change,
            cutoff,
        )
        self.assertIn(item.id, ids(initial))
        self.assertIn(item.id, ids(delta))
        self.assertIn(item.id, ids(full))

    def test_category_depth_and_fresh_cache_control(self):
        root = self.env["pos.category"].create({"name": "Root"})
        middle = self.env["pos.category"].create(
            {"name": "Middle", "parent_id": root.id}
        )
        leaf = self.env["pos.category"].create({"name": "Leaf", "parent_id": middle.id})
        before = leaf.display_name
        root.name = "Changed"
        stale = leaf.display_name
        self.env.invalidate_all()
        fresh = leaf.display_name
        self.assertEqual(before, "Root / Middle / Leaf")
        self.assertEqual(stale, "Changed / Middle / Leaf")
        self.assertEqual(fresh, "Changed / Middle / Leaf")
        log.debug("CHALLENGE category depth=3 stale=%r fresh=%r", stale, fresh)

    def test_dst_default_and_explicit_window_controls(self):
        report = self.env["report.point_of_sale.report_saledetails"].with_context(
            tz="America/New_York"
        )
        for day, expected_hour, next_day in [
            (date(2026, 3, 8), 23, False),
            (date(2026, 11, 1), 23, False),
            (date(2026, 9, 13), 23, False),
        ]:
            with patch.object(fields.Date, "context_today", return_value=day):
                start, stop = report._get_date_start_and_date_stop(False, False)
            local_stop = stop.replace(tzinfo=UTC).astimezone(
                ZoneInfo("America/New_York")
            )
            self.assertEqual(local_stop.hour, expected_hour)
            self.assertEqual(local_stop.date() > day, next_day)
            expected_stop = datetime.combine(
                day + timedelta(days=1),
                datetime.min.time(),
                ZoneInfo("America/New_York"),
            ).astimezone(UTC).replace(tzinfo=None) - timedelta(microseconds=1)
            explicit = report._get_date_start_and_date_stop(start, expected_stop)
            self.assertEqual(explicit, (start, expected_stop))
            log.debug(
                "CHALLENGE DST day=%s implicit_stop=%s explicit_stop_utc=%s",
                day,
                local_stop,
                explicit[1],
            )

    def test_tracked_no_variant_grouping(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.pos_config_usd.picking_type_id = warehouse.pos_type_id
        warehouse.pos_type_id.use_existing_lots = True
        attribute = self.env["product.attribute"].create(
            {"name": "Challenge inscription", "create_variant": "no_variant"}
        )
        values = self.env["product.attribute.value"].create(
            [{"name": label, "attribute_id": attribute.id} for label in ["A", "B"]]
        )
        product = self.env["product.product"].create(
            {
                "name": "Challenge group",
                "is_storable": True,
                "tracking": "lot",
                "available_in_pos": True,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(values.ids)],
                        }
                    )
                ],
            }
        )
        ptavs = product.attribute_line_ids.product_template_value_ids
        lot = self.env["stock.lot"].create(
            {
                "name": "GROUP-LOT",
                "product_id": product.id,
                "company_id": self.env.company.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 10, lot_id=lot
        )
        order = self._order(
            [
                {
                    "product_id": product.id,
                    "qty": 1,
                    "attribute_value_ids": [Command.set(ptav.ids)],
                    "pack_lot_ids": [Command.create({"lot_name": lot.name})],
                }
                for ptav in ptavs
            ]
        )
        order._create_order_picking()
        moves = order.picking_ids.move_ids
        log.debug(
            "CHALLENGE grouping ordered=%s demands=%s done_quantities=%s attrs=%s",
            sum(order.lines.mapped("qty")),
            moves.mapped("product_uom_qty"),
            moves.mapped("quantity"),
            [m.never_product_template_attribute_value_ids.ids for m in moves],
        )
        self.assertEqual(sum(order.lines.mapped("qty")), 2)
        self.assertEqual(sum(moves.mapped("quantity")), 2)

        reservation = order.picking_ids.copy({"move_ids": [Command.clear()]})
        groups = order.lines.grouped(lambda line: tuple(line.attribute_value_ids.ids))
        reserved_moves = (
            self.env["stock.move"]
            .create(
                [
                    reservation._prepare_stock_move_vals(lines)
                    for lines in groups.values()
                ]
            )
            ._action_confirm()
        )
        # Match the order procurement caller: replace the automatic reservation.
        reserved_moves.move_line_ids.unlink()
        reserved_moves._add_move_lines_from_pos_order_lines(
            order.lines, are_quantities_done=False
        )
        self.assertEqual(reserved_moves.mapped("quantity"), [1, 1])
        log.debug(
            "STOCK attribute reservation quantities=%s",
            reserved_moves.mapped("quantity"),
        )

    def _set_report_rates(self):
        company = self.env.company
        usd, eur = self.env.ref("base.USD"), self.env.ref("base.EUR")
        today = fields.Date.today()
        rates = self.env["res.currency.rate"].search(
            [("company_id", "=", company.id), ("currency_id", "in", (usd | eur).ids)]
        )
        rates.unlink()
        self.env["res.currency.rate"].create(
            [
                {
                    "company_id": company.id,
                    "currency_id": usd.id,
                    "name": today,
                    "rate": 1,
                },
                {
                    "company_id": company.id,
                    "currency_id": eur.id,
                    "name": today,
                    "rate": 0.5,
                },
            ]
        )

    def test_mixed_currency_report_and_single_currency_control(self):
        self._set_report_rates()
        product = self.env["product.product"].create(
            {
                "name": "Challenge report service",
                "type": "service",
                "available_in_pos": True,
                "taxes_id": [Command.clear()],
            }
        )
        orders = self.env["pos.order"]
        for config in [self.pos_config_usd, self.pos_config_eur]:
            orders |= self._order(
                [{"product_id": product.id, "qty": 1, "price_unit": 100}],
                config,
                paid=True,
            )
        report_model = self.env["report.point_of_sale.report_saledetails"]
        single = report_model.get_sale_details(session_ids=orders[0].session_id.ids)
        report = report_model.get_sale_details(session_ids=orders.session_id.ids)
        log.debug(
            "CHALLENGE currencies=%s converted=%s product_total=%s payments=%s single=%s",
            orders.currency_id.mapped("name"),
            report["currency"]["total_paid"],
            report["products_info"]["total"],
            report["total_paid"],
            single["currency"]["total_paid"],
        )
        self.assertEqual(
            single["currency"]["total_paid"], single["products_info"]["total"]
        )
        self.assertEqual(report["currency"]["total_paid"], 300)
        self.assertEqual(report["products_info"]["total"], 300)
        self.assertEqual(report["total_paid"], 300)

    def test_payment_guard_warm_cache(self):
        method = self.bank_payment_method
        before = method.open_session_ids
        self.assertFalse(before)
        session = self._session()
        cached = method.open_session_ids
        with self.assertRaises(UserError):
            method.write({"name": "Mutation while session open"})
        method.invalidate_recordset(["open_session_ids"])
        fresh = method.open_session_ids
        log.debug(
            "CHALLENGE payment guard cached=%s fresh=%s session=%s",
            cached.ids,
            fresh.ids,
            session.id,
        )
        self.assertIn(session, cached)
        self.assertIn(session, fresh)
        with self.assertRaises(UserError):
            method.write({"name": "Blocked after invalidation"})

    def test_partner_pagination_hidden_first_page(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "point_of_sale.limited_customer_count", "3"
        )
        partners = self.env["res.partner"].create(
            [{"name": f"000 Challenge Page {i}"} for i in range(6)]
        )
        ranked = [row[0] for row in self.pos_config_usd.get_limited_partners_loading()]
        self.assertEqual(ranked, partners[:3].ids)
        self.env["ir.rule"].sudo().create(
            {
                "name": "Challenge hide first page",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "domain_force": repr([("id", "not in", partners[:3].ids)]),
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        first = self.env["res.partner"].get_new_partner(self.pos_config_usd.id, [], 0)[
            "res.partner"
        ]
        client_offset = len(first) or 100
        actual_next = self.env["res.partner"].get_new_partner(
            self.pos_config_usd.id, [], client_offset
        )["res.partner"]
        correct_next = self.env["res.partner"].get_new_partner(
            self.pos_config_usd.id, [], 3
        )["res.partner"]
        log.debug(
            "CHALLENGE pagination ranked=%s first=%s client_offset=%s next=%s correct_next=%s",
            ranked,
            [r["id"] for r in first],
            client_offset,
            [r["id"] for r in actual_next],
            [r["id"] for r in correct_next],
        )
        self.assertEqual({r["id"] for r in first}, set(partners[3:].ids))
        self.assertFalse(set(partners.ids) & {r["id"] for r in actual_next})
        self.assertEqual(actual_next, correct_next)

    def test_disabled_lifecycle_logger_does_not_compute_label(self):
        from odoo.addons.point_of_sale.tools import debug_log as dbg

        method = self.bank_payment_method
        original = type(method)._compute_open_session_ids
        for enabled in [False, True]:
            calls = []

            def counted(records, calls=calls):
                calls.append(records.ids)
                return original(records)

            method.invalidate_recordset(["open_session_ids"])
            with (
                patch.object(type(method), "_compute_open_session_ids", counted),
                patch.object(dbg.lifecycle, "isEnabledFor", return_value=enabled),
            ):
                method.write({"sequence": method.sequence + 1})
            log.debug(
                "CHALLENGE debug-label lifecycle_enabled=%s computed_calls=%s",
                enabled,
                calls,
            )
            self.assertEqual(len(calls), int(enabled))

    def test_variant_timestamp_control_after_full_flush(self):
        product = self.env["product.product"].create(
            {"name": "Challenge variant timestamp", "available_in_pos": False}
        )
        cutoff = self.env.cr.now() - timedelta(hours=1)
        self._stamp(product, cutoff - timedelta(days=1))
        self._stamp(product.product_tmpl_id, cutoff - timedelta(days=1))
        product.product_tmpl_id.available_in_pos = True
        self.env.flush_all()
        product.invalidate_recordset(["write_date"])
        rows = (
            self.env["product.product"]
            .with_context(pos_last_server_date=fields.Datetime.to_string(cutoff))
            ._load_pos_data_search_read(
                {"product.template": [{"id": product.product_tmpl_id.id}]},
                self.pos_config_usd,
            )
        )
        log.debug(
            "CHALLENGE variant cutoff=%s persisted_write=%s ids=%s",
            cutoff,
            product.write_date,
            [r["id"] for r in rows],
        )
        self.assertGreater(product.write_date, cutoff)
        self.assertIn(product.id, [r["id"] for r in rows])

    def test_unbalanced_close_preserves_outer_transaction(self):
        product = self.env["product.product"].create(
            {
                "name": "Challenge unbalanced service",
                "type": "service",
                "available_in_pos": True,
                "taxes_id": [Command.clear()],
            }
        )
        order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 10}], paid=True
        )
        session = order.session_id
        original = type(session)._create_account_move

        def unbalanced(record, *args, **kwargs):
            result = original(record, *args, **kwargs)
            line = record.move_id.line_ids.filtered(lambda l: l.debit > 0)[:1]
            line.with_context(check_move_validity=False).write(
                {"debit": line.debit + 1}
            )
            log.debug(
                "CHALLENGE injected imbalance=%s into move=%s",
                sum(record.move_id.line_ids.mapped("balance")),
                record.move_id.id,
            )
            return result

        with patch.object(type(session), "_create_account_move", unbalanced):
            action = session.action_pos_session_closing_control()
        self.assertEqual(action["res_model"], "pos.close.session.wizard")
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "paid")
        self.assertFalse(session.move_id)
        session.action_pos_session_closing_control()
        self.assertEqual(session.state, "closed")
        log.debug(
            "CHALLENGE unbalanced close preserved order=%s and retry closed session=%s",
            order.id,
            session.id,
        )

    def test_report_converts_tax_discount_and_counting_amounts(self):
        self._set_report_rates()
        tax = self.env["account.tax"].create(
            {
                "name": "Report ten percent",
                "amount": 10,
                "amount_type": "percent",
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Discounted taxed service",
                "type": "service",
                "available_in_pos": True,
            }
        )
        orders = self.env["pos.order"]
        for config in [self.pos_config_usd, self.pos_config_eur]:
            orders |= self._order(
                [
                    {
                        "product_id": product.id,
                        "qty": 1,
                        "price_unit": 100,
                        "discount": 10,
                        "tax_ids": [Command.set(tax.ids)],
                    }
                ],
                config,
                paid=True,
            )
        report = self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            session_ids=orders.session_id.ids,
        )
        log.debug(
            "REPORT taxed currencies totals=%s taxes=%s discounts=%s payments=%s",
            report["currency"],
            report["taxes_info"],
            report["discount_amount"],
            report["payments"],
        )
        self.assertEqual(report["currency"]["total_paid"], 297)
        self.assertEqual(report["products_info"]["total"], 270)
        self.assertEqual(report["taxes_info"]["tax_amount"], 27)
        self.assertEqual(report["discount_amount"], 30)
        self.assertEqual(report["total_paid"], 297)

    def test_report_payments_use_the_order_exchange_date(self):
        self._set_report_rates()
        later = fields.Date.today() + timedelta(days=1)
        self.env["res.currency.rate"].create(
            {
                "company_id": self.env.company.id,
                "currency_id": self.env.ref("base.EUR").id,
                "name": later,
                "rate": 0.25,
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Dated service",
                "type": "service",
                "available_in_pos": True,
            }
        )
        orders = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}], paid=True
        )
        for day in [fields.Date.today(), later]:
            order = self._order(
                [{"product_id": product.id, "qty": 1, "price_unit": 100}],
                self.pos_config_eur,
                paid=True,
            )
            order.date_order = fields.Datetime.to_datetime(day)
            orders |= order
        report = self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            session_ids=orders.session_id.ids
        )
        log.debug(
            "REPORT date-sensitive sale=%s payments=%s",
            report["currency"]["total_paid"],
            report["total_paid"],
        )
        self.assertEqual(report["currency"]["total_paid"], 700)
        self.assertEqual(report["products_info"]["total"], 700)
        self.assertEqual(report["total_paid"], 700)

    def test_fiscal_position_updates_after_partner_property_change(self):
        partner = self.env["res.partner"].create({"name": "Changing fiscal position"})
        positions = self.env["account.fiscal.position"].create(
            [
                {"name": name, "company_id": self.env.company.id}
                for name in ["First", "Second"]
            ]
        )
        partner.property_account_position_id = positions[0]
        self.assertEqual(partner.fiscal_position_id, positions[0])
        partner.property_account_position_id = positions[1]
        self.assertEqual(partner.fiscal_position_id, positions[1])
        log.debug(
            "CACHE fiscal property change resolved position=%s",
            partner.fiscal_position_id.id,
        )

    def test_on_demand_partner_includes_country_and_state_without_mutating_domain(self):
        country = self.env.ref("base.aq")
        state = self.env["res.country.state"].create(
            {"name": "Research station", "code": "RS", "country_id": country.id}
        )
        partner = self.env["res.partner"].create(
            {"name": "Polar buyer", "country_id": country.id, "state_id": state.id}
        )
        domain = [("id", "=", partner.id)]
        result = self.env["res.partner"].get_new_partner(
            self.pos_config_usd.id, domain, 0
        )
        self.assertEqual(domain, [("id", "=", partner.id)])
        self.assertIn(country.id, [row["id"] for row in result["res.country"]])
        self.assertIn(state.id, [row["id"] for row in result["res.country.state"]])
        log.debug(
            "LOAD on demand partner=%s country=%s state=%s",
            partner.id,
            country.id,
            state.id,
        )

    def test_on_demand_partner_state_includes_its_country(self):
        country = self.env.ref("base.aq")
        state = self.env["res.country.state"].create(
            {
                "name": "State without partner country",
                "code": "SC",
                "country_id": country.id,
            }
        )
        partner = self.env["res.partner"].create(
            {"name": "State-only buyer", "state_id": state.id, "country_id": False}
        )
        self.assertFalse(partner.country_id)
        result = self.env["res.partner"].get_new_partner(
            self.pos_config_usd.id, [("id", "=", partner.id)], 0
        )
        countries = {row["id"] for row in result["res.country"]}
        states = {row["id"]: row for row in result["res.country.state"]}
        log.debug(
            "LOAD state-only partner=%s states=%s countries=%s",
            partner.id,
            states,
            countries,
        )
        self.assertIn(state.id, states)
        self.assertIn(states[state.id]["country_id"], countries)
        session_data = self._session().load_data([])
        self.assertIn(partner.id, {row["id"] for row in session_data["res.partner"]})
        self.assertIn(country.id, {row["id"] for row in session_data["res.country"]})
        self.assertIn(
            state.id, {row["id"] for row in session_data["res.country.state"]}
        )

    def test_pricelist_delta_contains_rules_for_unchanged_products(self):
        config = self.pos_config_usd
        pricelist = self.env["product.pricelist"].create(
            {"name": "Product scheduled prices"}
        )
        config.write(
            {
                "use_pricelist": True,
                "pricelist_id": pricelist.id,
                "available_pricelist_ids": [Command.set(pricelist.ids)],
            }
        )
        product = self.env["product.product"].create(
            {"name": "Unchanged priced product", "available_in_pos": True}
        )
        cutoff = self.env.cr.now() + timedelta(hours=1)
        item = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "product_id": product.id,
                "applied_on": "0_product_variant",
                "compute_price": "fixed",
                "fixed_price": 7,
                "date_start": cutoff + timedelta(days=1),
            }
        )
        session = self._session(config)
        delta = session.with_context(
            pos_last_server_date=fields.Datetime.to_string(cutoff)
        ).load_data([])
        self.assertNotIn(
            product.product_tmpl_id.id, [row["id"] for row in delta["product.template"]]
        )
        self.assertIn(item.id, [row["id"] for row in delta["product.pricelist.item"]])
        on_demand = config.get_pos_ui_product_pricelist_item_by_product(
            product.product_tmpl_id.ids, product.ids
        )
        self.assertIn(
            item.id, [row["id"] for row in on_demand["product.pricelist.item"]]
        )
        log.debug(
            "LOAD unchanged product=%s scheduled item=%s included in delta and on demand",
            product.id,
            item.id,
        )

    def test_foreign_session_counting_difference_uses_report_currency(self):
        self._set_report_rates()
        product = self.env["product.product"].create(
            {
                "name": "Counted foreign service",
                "type": "service",
                "available_in_pos": True,
            }
        )
        usd_order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}], paid=True
        )
        eur_order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}],
            self.pos_config_eur,
            paid=True,
        )
        eur_order.session_id.action_pos_session_closing_control(
            bank_payment_method_diffs={self.bank_payment_method.id: -10}
        )
        payment = self.env["account.payment"].search(
            [("pos_session_id", "=", eur_order.session_id.id)]
        )
        self.assertEqual(payment.currency_id, eur_order.currency_id)
        self.assertEqual(payment.amount, 90)
        outstanding = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == payment.outstanding_account_id
        )
        self.assertEqual(outstanding.amount_currency, 90)
        self.assertEqual(outstanding.balance, 180)
        report_model = self.env["report.point_of_sale.report_saledetails"]
        for orders, total, counted, difference in [
            (eur_order, 100, 90, -10),
            (usd_order | eur_order, 200, 180, -20),
        ]:
            report = report_model.get_sale_details(session_ids=orders.session_id.ids)
            row = next(
                row
                for row in report["payments"]
                if row["session"] == eur_order.session_id.id
                and row["id"] == self.bank_payment_method.id
            )
            log.debug("REPORT foreign closed count=%s", row)
            self.assertEqual(row["total"], total)
            self.assertEqual(row["money_counted"], counted)
            self.assertEqual(row["money_difference"], difference)
            self.assertEqual(
                sum(move["amount"] for move in row["cash_moves"]), difference
            )

    def test_split_foreign_bank_payment_keeps_session_currency(self):
        self._set_report_rates()
        self.bank_payment_method.split_transactions = True
        product = self.env["product.product"].create(
            {
                "name": "Split foreign service",
                "type": "service",
                "available_in_pos": True,
            }
        )
        order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}],
            self.pos_config_eur,
            paid=True,
        )
        order.session_id.action_pos_session_closing_control()
        payment = self.env["account.payment"].search(
            [("pos_session_id", "=", order.session_id.id)]
        )
        self.assertEqual(payment.currency_id, order.currency_id)
        self.assertEqual(payment.amount, 100)
        self.assertEqual(payment.amount_company_currency_signed, 200)
        log.debug(
            "ACCOUNT split foreign payment=%s currency=%s amount=%s company_amount=%s",
            payment.id,
            payment.currency_id.name,
            payment.amount,
            payment.amount_company_currency_signed,
        )

    def test_exchange_rate_change_is_not_a_cashier_counting_difference(self):
        self._set_report_rates()
        product = self.env["product.product"].create(
            {
                "name": "Currency count service",
                "type": "service",
                "available_in_pos": True,
            }
        )
        usd_order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}], paid=True
        )
        eur_order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}],
            self.pos_config_eur,
            paid=True,
        )
        eur_order.session_id.action_pos_session_closing_control()
        later = fields.Date.today() + timedelta(days=1)
        self.env["res.currency.rate"].create(
            {
                "company_id": self.env.company.id,
                "currency_id": eur_order.currency_id.id,
                "name": later,
                "rate": 0.25,
            }
        )
        eur_order.session_id.stop_at = fields.Datetime.to_datetime(later)
        report = self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            session_ids=(usd_order | eur_order).session_id.ids
        )
        row = next(
            row
            for row in report["payments"]
            if row["session"] == eur_order.session_id.id
            and row["id"] == self.bank_payment_method.id
        )
        self.assertEqual(row["total"], 200)
        self.assertEqual(row["money_counted"], 400)
        self.assertEqual(row["final_count"], 400)
        self.assertEqual(row["money_difference"], 0)
        log.debug("REPORT sale rate and closing rate differ without shortage: %s", row)

    def test_foreign_invoice_rows_and_totals_use_report_currency(self):
        self._set_report_rates()
        product = self.env["product.product"].create(
            {
                "name": "Foreign invoice service",
                "type": "service",
                "available_in_pos": True,
            }
        )
        usd_order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}], paid=True
        )
        eur_order = self._order(
            [{"product_id": product.id, "qty": 1, "price_unit": 100}],
            self.pos_config_eur,
            paid=True,
        )
        eur_order.action_pos_order_invoice()
        report_model = self.env["report.point_of_sale.report_saledetails"]
        for orders, expected in [(eur_order, 100), (eur_order | usd_order, 200)]:
            report = report_model.get_sale_details(session_ids=orders.session_id.ids)
            invoice_amount = sum(
                invoice["total"]
                for session in report["invoice_list"]
                for invoice in session["invoices"]
            )
            self.assertEqual(invoice_amount, expected)
            self.assertEqual(report["invoice_total"], expected)
            log.debug(
                "REPORT foreign invoice rows=%s total=%s",
                invoice_amount,
                report["invoice_total"],
            )
