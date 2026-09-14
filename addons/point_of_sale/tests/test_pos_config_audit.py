import os
import time
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.service.model import call_kw
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install", "-at_install")
class TestPosConfigAudit(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

    def test_pricelist_is_rechecked_when_only_its_company_changes(self):
        self.config.pricelist_id.company_id = self.config.company_id
        company = self.env["res.company"].create({"name": "Pricelist destination"})
        self.config.write(
            {
                "journal_id": False,
                "invoice_journal_id": False,
                "payment_method_ids": [Command.clear()],
                "available_pricelist_ids": [Command.clear()],
            }
        )

        with self.assertRaisesRegex(ValidationError, "default pricelist must belong"):
            self.config.write({"company_id": company.id})

    def test_printer_menu_tracks_archiving_and_deletion(self):
        self.env["pos.config"].search([]).write({"is_order_printer": False})
        menu = self.env.ref("point_of_sale.menu_pos_preparation_printer")
        for action in ("archive", "unlink"):
            with self.subTest(action=action):
                config = self.config.copy({"name": action, "is_order_printer": True})
                self.assertTrue(menu.active)

                if action == "archive":
                    config.with_context(active_test=False).action_archive()
                else:
                    config.unlink()

                self.assertFalse(menu.active)

    def test_open_and_rescue_sessions_prevent_archiving(self):
        session = self.env["pos.session"].create({"config_id": self.config.id})
        for rescue in (False, True):
            session.rescue = rescue
            with self.subTest(rescue=rescue), self.assertRaises(UserError):
                self.config.active = False

        self.config.write({"name": "Editable while open", "active": True})
        self.assertEqual(self.config.name, "Editable while open")

    def test_branch_payment_methods_belong_to_the_branch(self):
        branch = self.env["res.company"].create(
            {
                "name": "POS branch",
                "parent_id": self.config.company_id.id,
            }
        )

        branch_config = self.config.with_context(
            allowed_company_ids=[branch.id, self.config.company_id.id]
        )
        self.assertIn(self.bank_pm1, branch_config.env["pos.payment.method"].search([]))
        _journal, method_ids = branch_config._create_journal_and_payment_methods()

        methods = self.env["pos.payment.method"].browse(method_ids)
        self.assertEqual(set(methods.mapped("type")), {"cash", "bank", "pay_later"})
        self.assertEqual(methods.company_id, branch)

    def test_dates_do_not_depend_on_the_server_timezone(self):
        config = self.config.with_context(tz="UTC")
        session = self.env["pos.session"].create({"config_id": config.id})
        instant = fields.Datetime.to_datetime("2026-01-01 02:00:00")
        session.write({"start_at": instant, "stop_at": instant, "state": "closed"})

        try:
            with (
                patch.dict(os.environ, {"TZ": "Pacific/Kiritimati"}),
                patch.object(fields.Datetime, "now", return_value=instant),
            ):
                time.tzset()
                reference, _tracking = config._get_next_order_refs()
                self.assertTrue(reference.startswith("26"), reference)
                self.assertEqual(config.last_session_closing_date, instant.date())
                self.assertEqual(
                    config._get_statistics_for_session(session)["date"]["start_date"],
                    "Jan 01",
                )
                self.assertEqual(
                    config.with_context(
                        tz="Pacific/Honolulu"
                    ).last_session_closing_date,
                    fields.Date.to_date("2025-12-31"),
                )
        finally:
            time.tzset()

    def test_session_name_uses_the_config_company_sequence(self):
        other_company = self.env["res.company"].create({"name": "Active company"})
        sequence = (
            self.env["ir.sequence"]
            .sudo()
            .create(
                {
                    "name": "Config company sessions",
                    "code": "pos.session",
                    "company_id": self.config.company_id.id,
                    "prefix": "CONFIG/",
                    "padding": 3,
                }
            )
        )
        self.env["ir.sequence"].sudo().create(
            {
                "name": "Other company sessions",
                "code": "pos.session",
                "company_id": other_company.id,
                "prefix": "OTHER/",
            }
        )

        name = self.config.with_company(other_company)._get_next_session_name()

        self.assertEqual(name, "CONFIG/001")
        self.assertEqual(sequence.number_next_actual, 2)

    def test_closing_a_session_refreshes_cached_last_session(self):
        session = self.env["pos.session"].create({"config_id": self.config.id})
        self.assertFalse(self.config.last_session_closing_date)
        self.assertEqual(self.config.last_session_closing_cash, 0)

        session.write(
            {
                "state": "closed",
                "stop_at": fields.Datetime.to_datetime("2026-09-10 12:00:00"),
                "cash_register_balance_end_real": 42,
            }
        )

        self.assertEqual(self.config.last_session_closing_cash, 42)
        self.assertEqual(
            self.config.last_session_closing_date,
            session.stop_at.astimezone(self.env.tz).date(),
        )

    def test_rescue_change_refreshes_current_session_user(self):
        session = self.env["pos.session"].create({"config_id": self.config.id})
        self.assertEqual(self.config.current_user_id, session.user_id)

        session.rescue = True

        self.assertFalse(self.config.current_user_id)
        self.assertFalse(self.config.statistics_for_current_session)

    def test_opening_balance_refreshes_cached_statistics(self):
        session = self.env["pos.session"].create({"config_id": self.config.id})
        self.assertEqual(
            self.config.statistics_for_current_session["cash"]["raw_opening_cash"], 0
        )

        session.cash_register_balance_start = 42

        self.assertEqual(
            self.config.statistics_for_current_session["cash"]["raw_opening_cash"], 42
        )

    def test_payment_journal_change_refreshes_cash_control(self):
        method = self.env["pos.payment.method"].create(
            {
                "name": "Initially on account",
                "company_id": self.config.company_id.id,
            }
        )
        self.config.payment_method_ids = [Command.set(method.ids)]
        self.assertFalse(self.config.cash_control)

        method.journal_id = self.cash_pm1.journal_id

        self.assertTrue(self.config.cash_control)

    def test_settings_keeps_updates_to_linked_records(self):
        note = self.env["pos.note"].create({"name": "Before"})
        self.config.note_ids = note
        values = {
            "note_ids": [
                Command.link(note.id),
                Command.update(note.id, {"name": "After"}),
            ],
        }

        changed = self.config.with_context(
            from_settings_view=True
        )._prepare_vals_changed(values)
        self.assertEqual(
            note.name, "Before", "comparison must not write related records"
        )
        self.assertEqual(changed, values)

        self.config.with_context(from_settings_view=True).write(values)

        note.invalidate_recordset()
        self.assertEqual(note.name, "After")
        self.assertEqual(self.config.note_ids, note)

    def test_last_session_survives_a_closed_session_without_stop_at(self):
        session = self.env["pos.session"].create(
            {"config_id": self.config.id, "user_id": self.env.uid}
        )
        session.action_pos_session_closing_control()
        if session.state != "closed":
            session.action_pos_session_close()
        dated_stop_at = session.stop_at
        self.assertTrue(dated_stop_at)

        undated = self.env["pos.session"].create(
            {"config_id": self.config.id, "user_id": self.env.uid}
        )
        undated.action_pos_session_close()
        self.assertEqual(undated.state, "closed")
        self.assertFalse(undated.stop_at)

        self.env.invalidate_all()
        self.env["pos.config"].search([]).read(
            ["last_session_closing_date", "last_session_closing_cash"]
        )
        self.assertEqual(
            self.config.last_session_closing_date,
            dated_stop_at.astimezone(self.env.tz).date(),
        )

    def test_last_session_does_not_cost_a_query_per_config(self):
        def count_for(number_of_clones):
            configs = self.config
            for index in range(number_of_clones):
                configs |= self.config.copy(
                    {"name": f"clone-{number_of_clones}-{index}"}
                )
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            configs.mapped("last_session_closing_cash")
            return self.env.cr.sql_statement_count - before

        few = count_for(2)
        many = count_for(16)
        self.assertLessEqual(
            many,
            few,
            f"last_session_closing_cash cost {many} queries for 16 configs against "
            f"{few} for 2; it must not scale with the number of configs",
        )

    def test_pos_manager_can_delete_a_config(self):
        manager = self.env["res.users"].create(
            {
                "name": "PoS Manager",
                "login": "audit_pos_manager",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("point_of_sale.group_pos_manager").id,
                            self.env.ref("base.group_user").id,
                        ],
                    )
                ],
            }
        )
        config = self.config.copy({"name": "to-delete"})
        sequences = (
            config.order_seq_id
            | config.order_backend_seq_id
            | config.order_line_seq_id
            | config.device_seq_id
        )
        call_kw(self.env["pos.config"].with_user(manager), "unlink", [[config.id]], {})
        self.assertFalse(config.exists())
        self.assertFalse(sequences.exists())

    def test_read_config_open_orders_accepts_its_own_default(self):
        self.config.read_config_open_orders({"pos.order": []})

    def test_a_fully_refunded_order_is_not_counted_as_paid(self):
        session = self.env["pos.session"].create(
            {"config_id": self.config.id, "user_id": self.env.uid}
        )
        session.action_pos_session_open()
        product = self.env["product.product"].create(
            {
                "name": "Ten Cents",
                "available_in_pos": True,
                "list_price": 0.10,
                "taxes_id": [(5, 0, 0)],
            }
        )

        def make_order(amount, refunded_line=None):
            line = {
                "product_id": product.id,
                "qty": -1 if refunded_line else 1,
                "price_unit": abs(amount),
                "price_subtotal": amount,
                "price_subtotal_incl": amount,
            }
            if refunded_line:
                line["refunded_orderline_id"] = refunded_line.id
            order = self.env["pos.order"].create(
                {
                    "session_id": session.id,
                    "company_id": self.env.company.id,
                    "amount_tax": 0,
                    "amount_total": amount,
                    "amount_paid": amount,
                    "amount_return": 0,
                    "is_refund": bool(refunded_line),
                    "lines": [(0, 0, line)],
                }
            )
            order.state = "paid"
            return order

        order = make_order(0.10)
        make_order(-0.01, order.lines[0])
        make_order(-0.09, order.lines[0])
        self.env.invalidate_all()

        statistics = self.config._get_statistics_for_session(session)
        self.assertFalse(
            statistics["orders"]["paid"],
            "an order refunded in full is not an outstanding paid order",
        )

    def test_partner_paging_returns_each_partner_exactly_once(self):
        self.env["res.partner"].create(
            [
                {"name": "Tied Partner", "company_id": self.env.company.id}
                for _ in range(300)
            ]
        )
        page_size = self.config._get_limited_partner_count()
        seen = []
        for offset in range(0, 400, page_size):
            seen += [row[0] for row in self.config.get_limited_partners_loading(offset)]
        self.assertEqual(len(seen), len(set(seen)), "paging returned a partner twice")

    def test_archived_partners_do_not_consume_the_load_limit(self):
        archived = self.env["res.partner"].create(
            {"name": "Archived Partner", "company_id": self.env.company.id}
        )
        archived.active = False
        loaded = [row[0] for row in self.config.get_limited_partners_loading()]
        self.assertNotIn(archived.id, loaded)

    def test_the_client_payload_carries_no_dashboard_computes_and_no_blob(self):
        fields = self.env["pos.config"]._load_pos_data_fields(self.config)
        self.assertTrue(fields, "pos.config must enumerate its client fields")
        for excluded in (
            "customer_display_bg_img",
            "session_ids",
            "statistics_for_current_session",
            "last_session_closing_cash",
            "last_session_closing_date",
            "company_has_template",
            "is_installed_account_accountant",
            "pos_session_username",
        ):
            self.assertNotIn(excluded, fields)
        for required in ("id", "name", "company_id", "currency_id", "cash_control"):
            self.assertIn(required, fields)

    def test_special_products_are_the_configs_own(self):
        tip = self.env["product.product"].create(
            {"name": "Custom Tip", "available_in_pos": True}
        )
        self.config.tip_product_id = tip
        self.assertIn(tip, self.config._get_special_products())
        payload = self.env["pos.config"]._load_pos_data_read(self.config, self.config)
        self.assertIn(tip.id, payload[0]["_pos_special_products_ids"])

    def test_fiscal_positions_are_not_discarded_by_an_unrelated_write(self):
        position = self.env["account.fiscal.position"].create(
            {"name": "Audit FP", "company_id": self.env.company.id}
        )
        self.config.write(
            {
                "tax_regime_selection": True,
                "fiscal_position_ids": [(6, 0, position.ids)],
            }
        )
        self.config.write({"receipt_footer": "unrelated"})
        self.assertEqual(self.config.fiscal_position_ids, position)

    def test_fiscal_positions_can_be_set_without_touching_the_regime_flag(self):
        position = self.env["account.fiscal.position"].create(
            {"name": "Audit FP 2", "company_id": self.env.company.id}
        )
        config = self.config.copy({"name": "fp-target"})
        config.write({"fiscal_position_ids": [(6, 0, position.ids)]})
        self.assertEqual(config.fiscal_position_ids, position)

    def test_turning_the_tax_regime_off_clears_the_fiscal_positions(self):
        position = self.env["account.fiscal.position"].create(
            {"name": "Audit FP 3", "company_id": self.env.company.id}
        )
        self.config.write(
            {
                "tax_regime_selection": True,
                "fiscal_position_ids": [(6, 0, position.ids)],
            }
        )
        self.config.write({"tax_regime_selection": False})
        self.assertFalse(self.config.fiscal_position_ids)

    def test_emptying_the_fast_payment_list_turns_the_feature_off(self):
        methods = self.config.payment_method_ids
        self.config.write(
            {
                "use_fast_payment": True,
                "fast_payment_method_ids": [(6, 0, methods.ids[:1])],
            }
        )
        self.config.write({"payment_method_ids": [(3, methods.ids[0])]})
        self.assertFalse(self.config.use_fast_payment)

    def test_fast_payment_without_a_fast_method_is_refused(self):
        methods = self.config.payment_method_ids
        self.config.write(
            {
                "use_fast_payment": True,
                "fast_payment_method_ids": [(6, 0, methods.ids[:1])],
            }
        )
        with self.assertRaises(ValidationError):
            self.config.write(
                {
                    "use_fast_payment": True,
                    "payment_method_ids": [(3, methods.ids[0])],
                }
            )

    def test_a_pricelist_constraint_judges_each_config_on_its_own(self):
        shared = self.env["product.pricelist"].create(
            {
                "name": "No company pricelist",
                "company_id": False,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        owned = self.env["product.pricelist"].create(
            {
                "name": "Own company pricelist",
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        first = self.config.copy({"name": "pl-a", "pricelist_id": shared.id})
        second = self.config.copy({"name": "pl-b", "pricelist_id": owned.id})
        (first | second)._check_pricelists()

    def test_the_removed_helpers_stay_removed(self):
        for gone in (
            "_get_or_create_journal_id",
            "_get_or_create_payment_method_id",
            "_link_same_non_cash_payment_methods",
            "_check_groups_implied",
            "execute",
        ):
            self.assertFalse(
                hasattr(self.env["pos.config"], gone),
                f"{gone} was removed as dead code; reintroducing it needs a caller",
            )

    def test_a_config_can_be_created_for_a_company_other_than_the_active_one(self):
        company = self.env["res.company"].create({"name": "Audit Second Co"})
        self.env["account.chart.template"].try_loading(
            "generic_coa", company=company, install_demo=False
        )
        self.env.invalidate_all()
        config = self.env["pos.config"].create(
            {"name": "other-company-shop", "company_id": company.id}
        )
        self.assertEqual(config.company_id, company)
        self.assertEqual(config.picking_type_id.company_id, company)
        self.assertTrue(config.payment_method_ids)
        for method in config.payment_method_ids:
            self.assertEqual(method.company_id, company)

    def test_each_company_in_a_batch_gets_its_own_warehouse(self):
        company = self.env["res.company"].create({"name": "Audit Third Co"})
        self.env["account.chart.template"].try_loading(
            "generic_coa", company=company, install_demo=False
        )
        self.env["stock.warehouse"].search([("company_id", "=", company.id)]).unlink()
        self.env.invalidate_all()
        self.env["pos.config"].with_context(
            allowed_company_ids=[self.env.company.id, company.id]
        ).create([{"name": "Alpha"}, {"name": "Bravo", "company_id": company.id}])
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)]
        )
        self.assertTrue(warehouse, "the second company got no warehouse")
        self.assertEqual(warehouse.code.upper(), "BRA")

    def test_order_refs_survive_a_prefixed_sequence(self):
        self.config.order_backend_seq_id.sudo().prefix = "/AA"
        self.env.invalidate_all()
        reference, tracking_number = self.config._get_next_order_refs()
        self.assertTrue(reference)
        self.assertTrue(tracking_number.isdigit())
