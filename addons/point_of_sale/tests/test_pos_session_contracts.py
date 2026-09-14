from datetime import timedelta

import odoo
from odoo import fields
from odoo.exceptions import UserError

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionComputeDependencies(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("SessionProd", self.categ_basic, 100, 50)

    def _paid_order(self, uuid):
        return self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.cash_pm1, 100)],
                    "uuid": uuid,
                }
            ]
        )[uuid]

    def test_cash_register_difference_follows_the_counted_amount(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self._paid_order("dep-diff-1")

        self.assertEqual(session.cash_register_difference, -100.0)
        session.cash_register_balance_end_real = 120.0

        self.assertEqual(
            session.cash_register_difference,
            20.0,
            "cash_register_difference is read from the counted amount, so writing"
            " that amount has to invalidate it",
        )

    def test_cash_register_balance_end_follows_a_new_payment(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self.assertEqual(session.cash_register_balance_end, 0.0)

        self._paid_order("dep-end-1")

        self.assertEqual(session.cash_register_balance_end, 100.0)

    def test_cash_register_balance_end_follows_a_cash_move(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self._paid_order("dep-move-1")
        self.assertEqual(session.cash_register_balance_end, 100.0)

        session.try_cash_in_out("in", 30, "float", self.env.user.partner_id.id, {})

        self.assertEqual(
            session.cash_register_balance_end,
            130.0,
            "cash_register_balance_end sums statement_line_ids, so creating one"
            " must invalidate it",
        )

    def test_total_payments_amount_follows_a_new_payment(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self.assertEqual(session.total_payments_amount, 0.0)

        self._paid_order("dep-total-1")

        self.assertEqual(session.total_payments_amount, 100.0)

    def test_total_payments_amount_follows_the_order_state(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        order = self._paid_order("dep-state-1")
        order.invalidate_recordset()
        self.env.cr.execute(
            "UPDATE pos_order SET state = 'draft' WHERE id = %s", (order.id,)
        )
        order.invalidate_recordset()
        self.env.invalidate_all()
        self.assertEqual(
            session.total_payments_amount,
            0.0,
            "a draft order's payments are outside the captured-payments domain",
        )

        order.state = "paid"

        self.assertEqual(
            session.total_payments_amount,
            100.0,
            "the domain filters on pos_order_id.state, so the total must be"
            " invalidated when an order enters 'paid' — no payment amount moved",
        )

    def test_order_count_follows_a_new_order(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self.assertEqual(session.order_count, 0)

        self._paid_order("dep-count-1")

        self.assertEqual(
            session.order_count,
            1,
            "order_count is computed from order_ids and must be invalidated with it",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionClosingGuards(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_closing_an_empty_session_twice_is_refused(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.action_pos_session_closing_control()
        self.assertEqual(session.state, "closed")

        with self.assertRaises(UserError):
            session._close_session()

    def test_the_force_close_action_carries_the_bank_differences(self):
        session = self._start_pos_session(self.cash_pm1 | self.bank_split_pm1, 0)
        diffs = {self.bank_split_pm1.id: 3.0}

        action = session._open_force_close_wizard(1.0, diffs)

        self.assertEqual(action["context"]["bank_payment_method_diffs"], diffs)

    def test_the_force_close_wizard_forwards_the_bank_differences(self):
        session = self._start_pos_session(self.cash_pm1 | self.bank_split_pm1, 0)
        diffs = {self.bank_split_pm1.id: 3.0}
        forwarded = []

        def spy(
            records,
            balancing_account=False,
            amount_to_balance=0,
            bank_payment_method_diffs=None,
        ):
            forwarded.append(bank_payment_method_diffs)
            return True

        action = session._open_force_close_wizard(1.0, diffs)
        wizard = self.env["pos.close.session.wizard"].browse(action["res_id"])
        self.patch(type(session), "action_pos_session_closing_control", spy)

        wizard.with_context(action["context"]).action_close_session()

        self.assertEqual(
            forwarded,
            [diffs],
            "a forced close must post the bank differences the cashier entered",
        )

    def test_the_force_close_wizard_repairs_json_string_keys(self):
        session = self._start_pos_session(self.cash_pm1 | self.bank_split_pm1, 0)
        forwarded = []

        def spy(
            records,
            balancing_account=False,
            amount_to_balance=0,
            bank_payment_method_diffs=None,
        ):
            forwarded.append(bank_payment_method_diffs)
            return True

        action = session._open_force_close_wizard(1.0, {})
        wizard = self.env["pos.close.session.wizard"].browse(action["res_id"])
        self.patch(type(session), "action_pos_session_closing_control", spy)

        wizard.with_context(
            {
                **action["context"],
                "bank_payment_method_diffs": {str(self.bank_split_pm1.id): 3.0},
            }
        ).action_close_session()

        self.assertEqual(
            forwarded,
            [{self.bank_split_pm1.id: 3.0}],
            "the context round-trips through json, which turns the payment method"
            " ids into strings",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionCashMoves(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_an_unknown_partner_message_type_is_refused(self):
        session = self._start_pos_session(self.cash_pm1, 0)

        with self.assertRaises(UserError):
            session.log_partner_message(
                self.env.user.partner_id.id, "some action", "NOT_A_MESSAGE_TYPE"
            )

    def test_a_cash_move_without_a_partner_can_be_removed(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.try_cash_in_out("in", 50, "reason", False, {})
        statement_line = session.statement_line_ids[0]
        self.assertFalse(statement_line.partner_id)

        session.remove_cash_in_out(statement_line.id, self.env.user.partner_id.id)

        self.assertFalse(statement_line.exists())

    def test_the_captured_payments_domain_names_live_order_states(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        order_states = {
            value for value, _label in self.env["pos.order"]._fields["state"].selection
        }

        for field_path, _operator, value in session._get_domain_captured_payments():
            if field_path == "pos_order_id.state":
                self.assertLessEqual(
                    set(value),
                    order_states,
                    "the domain names a pos.order state this fork does not have",
                )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionLoadContract(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_a_related_many2many_reports_its_relation_table(self):
        session = self._start_pos_session(self.cash_pm1, 0)

        relations = session._get_field_relations("pos.session", ["payment_method_ids"])

        self.assertEqual(
            relations["payment_method_ids"]["relation_table"],
            self.env["pos.config"]._fields["payment_method_ids"].relation,
            "the client pairs many2many inverses by relation_table, so a related"
            " many2many has to report the table of the field it follows",
        )

    def test_no_loaded_many2many_reports_a_null_relation_table(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        params = session.load_data_params()

        nameless = [
            f"{model}.{name}"
            for model, spec in params.items()
            for name, relation in spec["relations"].items()
            if relation.get("type") == "many2many"
            and relation.get("relation_table") is None
            and self.env[model]._fields[name].related
        ]

        self.assertFalse(
            nameless, "these related many2many fields ship a null relation_table"
        )

    def test_get_session_orders_keeps_the_model_ordering(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        product = self.create_product("OrderProd", self.categ_basic, 100, 50)
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [(self.cash_pm1, 100)],
                    "uuid": f"ordering-{index}",
                }
                for index in range(4)
            ]
        )

        self.assertEqual(
            session.get_session_orders().ids,
            self.env["pos.order"].search([("session_id", "=", session.id)]).ids,
            "get_session_orders must keep pos.order._order: its result is shown"
            " to the user by _check_no_draft_orders and close_session_from_ui."
            " A version of this that filtered order_ids in place returned them"
            " ascending and nothing else caught it.",
        )

    def test_get_session_orders_matches_the_session_orders(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        product = self.create_product("LoadProd", self.categ_basic, 100, 50)
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [(self.cash_pm1, 100)],
                    "uuid": f"load-{index}",
                }
                for index in range(3)
            ]
        )

        self.assertEqual(
            session.get_session_orders().ids,
            session.order_ids.sorted().ids,
        )

    def test_get_session_orders_excludes_a_future_preset(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        product = self.create_product("PresetProd", self.categ_basic, 100, 50)
        order = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [(self.cash_pm1, 100)],
                    "uuid": "preset-1",
                }
            ]
        )["preset-1"]
        order.preset_time = fields.Datetime.now() + timedelta(days=1)

        self.assertNotIn(order, session.get_session_orders())


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionRoundingLine(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_a_rounding_line_is_built_from_the_company_amount_alone(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self.config.cash_rounding = True

        vals = session._prepare_rounding_difference_vals(0.0, 5.0)

        self.assertIsNotNone(
            vals,
            "a difference that rounds to zero in the session currency but not in the"
            " company currency still has to produce a line",
        )
        self.assertEqual(vals["credit"], 5.0)

    def test_no_rounding_line_when_both_amounts_are_zero(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self.config.cash_rounding = True

        self.assertIsNone(session._prepare_rounding_difference_vals(0.0, 0.0))


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionCashDetailsMessage(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_the_closing_notes_are_labelled_as_closing_notes(self):
        session = self._start_pos_session(self.cash_pm1, 0)

        session.update_closing_control_state_session("counted short")

        body = session.message_ids[0].body
        self.assertIn("counted short", body)
        self.assertNotIn("Opening control message", body)

    def test_the_opening_notes_are_labelled_as_opening_notes(self):
        session = self.env["pos.session"].create({"config_id": self.config.id})

        session.set_opening_control(0, "float checked")

        body = session.message_ids[0].body
        self.assertIn("float checked", body)
        self.assertIn("Opening control message", body)


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionClosingPicking(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("PickingProd", self.categ_basic, 100, 50)
        self.adjust_inventory([self.product], [100])

    def test_a_closing_picking_is_linked_to_its_session(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.update_stock_at_closing = True
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 2)],
                    "payments": [(self.cash_pm1, 200)],
                    "uuid": "picking-1",
                }
            ]
        )

        session._create_picking_at_end_of_session()

        self.assertTrue(session.picking_ids, "closing the session must move stock")
        self.assertEqual(
            session.picking_ids.pos_session_id,
            session,
            "a picking created at session closing carries the session that made it;"
            " _accumulate_stock_amounts finds these pickings by that link and by the"
            " absence of pos_order_id",
        )
        self.assertEqual(set(session.picking_ids.mapped("origin")), {session.name})
        self.assertFalse(
            session.picking_ids.pos_order_id,
            "a session-closing picking belongs to no single order",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionMultiRecord(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_get_session_orders_accepts_more_than_one_session(self):
        first = self._start_pos_session(self.cash_pm1, 0)
        first.action_pos_session_closing_control()
        second = self.env["pos.session"].create({"config_id": self.config.id})

        self.assertEqual((first | second).get_session_orders(), self.env["pos.order"])


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionOldSessionAlert(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def _age(self, session):
        session.start_at = fields.Datetime.now() - timedelta(days=8)
        return session

    def test_an_old_session_is_alerted_once_and_only_once(self):
        session = self._age(self._start_pos_session(self.cash_pm1, 0))

        self.env["pos.session"]._alert_old_sessions()
        first = self.env["mail.activity"].search_count(
            [("res_model", "=", "pos.session"), ("res_id", "=", session.id)]
        )
        self.env["pos.session"]._alert_old_sessions()
        second = self.env["mail.activity"].search_count(
            [("res_model", "=", "pos.session"), ("res_id", "=", session.id)]
        )

        self.assertEqual(first, 1)
        self.assertEqual(second, 1, "an already-alerted session must not be re-alerted")

    def test_the_alert_costs_one_query_for_the_whole_batch(self):
        for index in range(5):
            config = self.basic_config.copy({"name": f"alert-cfg-{index}"})
            method = self.cash_pm1.copy({"name": f"alert-cash-{index}"})
            config.write({"payment_method_ids": [(6, 0, method.ids)]})
            config.open_ui()
            self._age(config.current_session_id)
        self.env.flush_all()
        self.env.invalidate_all()

        before = self.cr.sql_statement_count
        self.env["pos.session"]._alert_old_sessions()
        first_run = self.cr.sql_statement_count - before

        self.env.invalidate_all()
        before = self.cr.sql_statement_count
        self.env["pos.session"]._alert_old_sessions()
        second_run = self.cr.sql_statement_count - before

        self.assertLessEqual(
            second_run,
            4,
            f"the already-alerted lookup should not scale with the batch"
            f" (5 sessions cost {second_run} queries; first run was {first_run})",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionLoadsItself(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_load_data_still_returns_the_session_itself(self):
        session = self._start_pos_session(self.cash_pm1, 0)

        payload = session.load_data([])

        self.assertEqual(
            [row["id"] for row in payload["pos.session"]],
            [session.id],
            "the session loads itself; it must not return a sibling or nothing",
        )

    def test_the_session_reads_itself_without_searching(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        searched = []
        original = type(session).search

        def spy(records, *args, **kwargs):
            searched.append(args[0] if args else None)
            return original(records, *args, **kwargs)

        self.patch(type(session), "search", spy)
        session._load_pos_data_search_read({}, session.config_id)

        self.assertFalse(
            searched,
            "the session already holds the record it is loading; searching for it"
            f" is the query this change removed (searched: {searched})",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionPaymentPayload(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_pos_payment_declares_its_field_list(self):
        declared = self.env["pos.payment"]._load_pos_data_fields(self.config)

        self.assertTrue(
            declared, "pos.payment must declare a field list, not fall back to []"
        )

    def test_no_unstored_compute_joins_the_payment_payload_by_accident(self):
        declared = set(self.env["pos.payment"]._load_pos_data_fields(self.config))
        allowed = self.env["pos.payment"]._get_pos_client_computed_fields()

        leaked = {
            name
            for name in declared
            if not self.env["pos.payment"]._fields[name].store and name not in allowed
        }

        self.assertFalse(
            leaked,
            "a non-stored compute reached the POS payload without being named:"
            f" {sorted(leaked)}",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosConfigPricelistPayload(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("PriceProd", self.categ_basic, 100, 50)

    def test_the_config_answers_without_a_session(self):
        self.assertFalse(self.config.current_session_id)

        rows = self.config.get_pos_ui_product_pricelist_item_by_product(
            self.product.product_tmpl_id.ids, self.product.ids
        )

        self.assertEqual(sorted(rows), ["product.pricelist", "product.pricelist.item"])

    def test_the_session_form_delegates_on_the_argument(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        other = self.basic_config.copy({"name": "pricelist-other"})

        by_session = session.get_pos_ui_product_pricelist_item_by_product(
            self.product.product_tmpl_id.ids, self.product.ids, other.id
        )
        by_config = other.get_pos_ui_product_pricelist_item_by_product(
            self.product.product_tmpl_id.ids, self.product.ids
        )

        self.assertEqual(
            by_session,
            by_config,
            "the session form must answer for the config it is handed, not its own",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionCashMoveCurrency(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_a_zero_amount_is_refused_for_every_session_not_just_the_first(self):
        first = self._start_pos_session(self.cash_pm1, 0)
        other_config = self.basic_config.copy({"name": "cashmove-other"})
        other_method = self.cash_pm1.copy(
            {
                "name": "cashmove-other-cash",
                "journal_id": self.env["account.journal"]
                .create({"name": "cashmove-other", "code": "CMOT", "type": "cash"})
                .id,
            }
        )
        other_config.write({"payment_method_ids": [(6, 0, other_method.ids)]})
        other_config.open_ui()
        second = other_config.current_session_id

        with self.assertRaises(UserError):
            (first | second).try_cash_in_out(
                "in", 0, "reason", self.env.user.partner_id.id, {}
            )

    def test_a_valid_amount_still_reaches_every_session(self):
        first = self._start_pos_session(self.cash_pm1, 0)
        other_config = self.basic_config.copy({"name": "cashmove-ok"})
        other_method = self.cash_pm1.copy(
            {
                "name": "cashmove-ok-cash",
                "journal_id": self.env["account.journal"]
                .create({"name": "cashmove-ok", "code": "CMOK", "type": "cash"})
                .id,
            }
        )
        other_config.write({"payment_method_ids": [(6, 0, other_method.ids)]})
        other_config.open_ui()
        second = other_config.current_session_id

        (first | second).try_cash_in_out(
            "in", 25, "float", self.env.user.partner_id.id, {}
        )

        self.assertEqual(sum(first.statement_line_ids.mapped("amount")), 25.0)
        self.assertEqual(sum(second.statement_line_ids.mapped("amount")), 25.0)

    def test_a_session_without_a_cash_journal_refuses_rather_than_being_skipped(self):
        with_cash = self._start_pos_session(self.cash_pm1, 0)
        bank_config = self.basic_config.copy({"name": "cashmove-bankonly"})
        bank_method = self.bank_pm1.copy({"name": "cashmove-bankonly-bank"})
        bank_config.write({"payment_method_ids": [(6, 0, bank_method.ids)]})
        bank_config.open_ui()
        without_cash = bank_config.current_session_id
        self.assertFalse(without_cash.cash_journal_id)

        with self.assertRaises(UserError):
            (with_cash | without_cash).try_cash_in_out(
                "in", 25, "float", self.env.user.partner_id.id, {}
            )

        self.assertFalse(
            with_cash.statement_line_ids,
            "refusing the batch must not leave a partial posting behind",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionPaidOrdersReachDone(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("DoneProd", self.categ_basic, 100, 50)

    def test_paid_orders_reach_done_even_when_the_entry_has_no_lines(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        order = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.cash_pm1, 100)],
                    "uuid": "done-1",
                }
            ]
        )["done-1"]
        self.assertEqual(order.state, "paid")

        session.action_pos_session_closing_control()

        self.assertEqual(
            order.state,
            "done",
            "a closed session leaves no order behind in 'paid'",
        )
        self.assertNotIn(
            "paid",
            session.order_ids.mapped("state"),
            "and that holds for every order in the session",
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionDiffMoveLink(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("DiffProd", self.categ_basic, 100, 50)

    def test_a_difference_entry_is_found_by_its_link_not_its_label(self):
        session = self._start_pos_session(self.cash_pm1 | self.bank_split_pm1, 0)
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.bank_split_pm1, 100)],
                    "customer": self.customer,
                    "uuid": "diff-1",
                }
            ]
        )
        session._create_diff_account_move_for_payment_method(
            self.bank_split_pm1, 5.0
        )

        diff = self.env["account.move"].search(
            [("pos_diff_session_id", "=", session.id)]
        )

        self.assertTrue(diff, "the difference entry must carry its session")
        self.assertIn(
            diff,
            session._get_other_related_moves(),
            "and the lookup must find it by that link",
        )

    def test_an_entry_with_the_same_label_elsewhere_is_not_claimed(self):
        session = self._start_pos_session(self.cash_pm1 | self.bank_split_pm1, 0)
        impostor = self.env["account.move"].create(
            {
                "journal_id": self.company_data["default_journal_misc"].id,
                "ref": session._get_diff_account_move_ref(self.bank_split_pm1),
            }
        )

        self.assertNotIn(
            impostor,
            session._get_other_related_moves(),
            "a same-ref entry in another journal is not this session's difference",
        )
