import logging
import unittest

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosConfigChallenge(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.product = cls.env["product.product"].create(
            {
                "name": "Challenge product",
                "available_in_pos": True,
                "taxes_id": [Command.clear()],
            }
        )

    def _create_session(self, **values):
        return self.env["pos.session"].create({"config_id": self.config.id, **values})

    def _create_order(self, session, amount=10, refunded_line=None):
        return self.env["pos.order"].create(
            {
                "session_id": session.id,
                "company_id": self.config.company_id.id,
                "amount_total": amount,
                "amount_tax": 0,
                "amount_paid": amount,
                "amount_return": 0,
                "is_refund": bool(refunded_line),
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "qty": -1 if refunded_line else 1,
                            "price_unit": abs(amount),
                            "price_subtotal": amount,
                            "price_subtotal_incl": amount,
                            "refunded_orderline_id": refunded_line.id
                            if refunded_line
                            else False,
                        }
                    )
                ],
            }
        )

    def test_cached_statistics_follow_order_lifecycle(self):
        session = self._create_session()
        self.assertFalse(self.config.statistics_for_current_session["orders"]["draft"])
        order = self._create_order(session)
        self.assertEqual(
            self.config.statistics_for_current_session["orders"]["draft"]["amount"], 10
        )

        order.amount_total = 12
        self.assertEqual(
            self.config.statistics_for_current_session["orders"]["draft"]["amount"], 12
        )
        order.state = "paid"
        stats = self.config.statistics_for_current_session["orders"]
        self.assertFalse(stats["draft"])
        self.assertEqual(stats["paid"]["amount"], 12)
        cancelled = self._create_order(session)
        self.assertEqual(
            self.config.statistics_for_current_session["orders"]["draft"]["count"], 1
        )
        cancelled.state = "cancel"
        self.assertEqual(
            self.config.statistics_for_current_session["orders"]["paid"]["amount"], 12
        )
        cancelled.unlink()
        self.assertFalse(self.config.statistics_for_current_session["orders"]["draft"])

    def test_refund_of_previous_session_remains_visible(self):
        old_session = self._create_session()
        sale = self._create_order(old_session)
        sale.state = "paid"
        old_session.write({"state": "closed", "stop_at": fields.Datetime.now()})
        current = self._create_session()
        refund = self._create_order(current, -10, sale.lines)
        refund.state = "paid"
        statistics = self.config.statistics_for_current_session["orders"]["paid"]
        _logger.debug("Refund-only session dashboard: %s", statistics)
        self.assertTrue(statistics)
        self.assertEqual(statistics["amount"], -10)
        self.assertEqual(statistics["count"], 0)

    def test_free_paid_order_is_counted(self):
        session = self._create_session()
        order = self._create_order(session, 0)
        order.state = "paid"
        statistics = self.config.statistics_for_current_session["orders"]["paid"]
        _logger.debug("Free paid order dashboard: %s", statistics)
        self.assertTrue(statistics)
        self.assertEqual(statistics["amount"], 0)
        self.assertEqual(statistics["count"], 1)

    def test_settings_update_preserves_payment_method_membership(self):
        methods = self.config.payment_method_ids
        method = methods[:1]
        self.config.with_context(from_settings_view=True).write(
            {
                "payment_method_ids": [
                    Command.update(method.id, {"name": "Updated in settings"})
                ],
            }
        )
        _logger.debug(
            "Settings update methods before=%s after=%s",
            methods.ids,
            self.config.payment_method_ids.ids,
        )
        self.assertEqual(self.config.payment_method_ids, methods)
        self.assertEqual(method.name, "Updated in settings")

    def test_settings_unlink_preserves_other_payment_methods(self):
        methods = self.config.payment_method_ids
        self.assertGreater(len(methods), 1)
        self.config.with_context(from_settings_view=True).write(
            {
                "payment_method_ids": [Command.unlink(methods[0].id)],
            }
        )
        _logger.debug(
            "Settings unlink methods before=%s after=%s",
            methods.ids,
            self.config.payment_method_ids.ids,
        )
        self.assertEqual(self.config.payment_method_ids, methods[1:])

    def test_trusted_configs_cannot_cross_company_boundaries(self):
        company = self.env["res.company"].create({"name": "Foreign trust company"})
        self.env["account.chart.template"].try_loading(
            "generic_coa", company=company, install_demo=False
        )
        other = self.env["pos.config"].create(
            {"name": "Foreign trust", "company_id": company.id}
        )
        config = self.config.with_context(
            allowed_company_ids=[self.config.company_id.id, company.id]
        )
        self.assertEqual(config.currency_id, other.currency_id)
        _logger.debug(
            "Rejecting trust across companies %s and %s",
            config.company_id.id,
            company.id,
        )
        with (
            self.assertRaisesRegex(ValidationError, "same company"),
            self.env.cr.savepoint(),
        ):
            config.trusted_config_ids = other

        target = config.copy({"name": "Incoming trust target"})
        config.trusted_config_ids = target
        config.active = False
        _logger.debug("Checking incoming trust from archived config %s", config.id)
        with (
            self.assertRaisesRegex(ValidationError, "same company"),
            self.env.cr.savepoint(),
        ):
            target.write(
                {
                    "company_id": company.id,
                    "journal_id": other.journal_id.id,
                    "invoice_journal_id": other.invoice_journal_id.id,
                    "picking_type_id": other.picking_type_id.id,
                    "pricelist_id": False,
                    "available_pricelist_ids": [Command.clear()],
                    "payment_method_ids": [Command.clear()],
                }
            )

    def test_synchronisation_rechecks_changed_journal_currency(self):
        target = self.config.copy({"name": "Currency trust target"})
        target.journal_id = self.config.journal_id.copy({"name": "Trust journal"})
        self.config.trusted_config_ids = target
        currency = (
            self.env["res.currency"]
            .with_context(active_test=False)
            .search([("id", "!=", self.config.currency_id.id)], limit=1)
        )
        currency.active = True
        target.journal_id.currency_id = currency
        _logger.debug(
            "Synchronization currency source=%s target=%s",
            self.config.currency_id.id,
            target.currency_id.id,
        )
        with self.assertRaisesRegex(ValidationError, "same currency"):
            self.config.notify_synchronisation(False, "challenge")

    def test_tip_fallback_excludes_foreign_and_archived_products(self):
        foreign = self.env["res.company"].create({"name": "Foreign tips"})
        default = self.env.ref("point_of_sale.product_product_tip")
        default.company_id = foreign
        local = self.product.copy(
            {"default_code": "TIPS", "company_id": self.env.company.id}
        )
        configs = self.env["pos.config"].with_context(
            allowed_company_ids=[self.env.company.id, foreign.id], active_test=False
        )
        _logger.debug(
            "Tip fallback company=%s foreign=%s local=%s",
            self.env.company.id,
            default.id,
            local.id,
        )
        self.assertEqual(configs._default_tip_product_id(), local)
        local.active = False
        self.assertFalse(configs._default_tip_product_id())

    def test_tip_reset_uses_configuration_company(self):
        foreign = self.env["res.company"].create({"name": "Active foreign tips"})
        default = self.env.ref("point_of_sale.product_product_tip")
        default.company_id = foreign
        local = self.product.copy(
            {"default_code": "TIPS", "company_id": self.config.company_id.id}
        )
        config = self.config.with_context(
            allowed_company_ids=[foreign.id, self.config.company_id.id]
        )
        config.write({"iface_tipproduct": True, "tip_product_id": False})
        _logger.debug(
            "Tip reset active company=%s config company=%s product=%s",
            foreign.id,
            config.company_id.id,
            config.tip_product_id.id,
        )
        self.assertEqual(config.tip_product_id, local)

    def test_explicit_foreign_tip_is_rejected(self):
        foreign = self.env["res.company"].create({"name": "Explicit foreign tip"})
        product = self.product.copy({"company_id": foreign.id})
        config = self.config.with_context(
            allowed_company_ids=[self.config.company_id.id, foreign.id]
        )
        _logger.debug(
            "Rejecting explicit foreign tip %s for config %s", product.id, config.id
        )
        with self.assertRaises(UserError):
            config.tip_product_id = product

    def test_cash_journal_preserves_explicit_default_account(self):
        Account = self.env["account.account"]
        fallback = Account.create(
            {
                "name": "Cash",
                "code": "CHCASH1",
                "account_type": "asset_cash",
                "company_ids": [Command.set(self.env.company.root_id.ids)],
            }
        )
        explicit = fallback.copy({"name": "Dedicated POS cash", "code": "CHCASH2"})
        method = self.env["pos.config"]._create_cash_payment_method(
            {"default_account_id": explicit.id}
        )
        _logger.debug(
            "Cash provisioning explicit=%s selected=%s",
            explicit.id,
            method.journal_id.default_account_id.id,
        )
        self.assertEqual(method.journal_id.default_account_id, explicit)

    def test_current_session_does_not_fetch_closed_history(self):
        closed = self._create_session()
        closed.write({"state": "closed", "stop_at": fields.Datetime.now()})
        current = self._create_session()
        rescue = self._create_session(rescue=True)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.config.current_session_id, current)
        self.assertEqual(self.config.number_of_rescue_session, 1)
        self.assertTrue(self.config.has_active_session)
        loaded = self.env.cache.contains(closed, closed._fields["state"])
        _logger.debug(
            "Closed session %s state loaded=%s; rescue=%s", closed.id, loaded, rescue.id
        )
        self.assertFalse(
            loaded, "Selecting an open session must not load closed history"
        )

    def test_current_session_selection_is_batched(self):
        configs = self.config | self.config.copy({"name": "Second session batch"})
        sessions = self.env["pos.session"].create(
            [{"config_id": config.id} for config in configs]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        # Warm access-rule metadata; session fields and computed values stay cold.
        self.env["pos.session"].search([], limit=1)
        with self.assertQueryCount(1):
            selected = configs.current_session_id
        _logger.debug("Batched current sessions: %s", configs.current_session_id.ids)
        self.assertEqual(selected, sessions)

    def test_batch_tip_reset_uses_each_configuration_company(self):
        company = self.env["res.company"].create({"name": "Batch tip company"})
        self.env["account.chart.template"].try_loading(
            "generic_coa", company=company, install_demo=False
        )
        other = self.env["pos.config"].create(
            {"name": "Other tips", "company_id": company.id}
        )
        default = self.env.ref("point_of_sale.product_product_tip")
        default.company_id = company
        local = self.product.copy(
            {"default_code": "TIPS", "company_id": self.config.company_id.id}
        )
        configs = (self.config | other).with_context(
            allowed_company_ids=[self.config.company_id.id, company.id]
        )
        configs.write(
            {
                "iface_tipproduct": True,
                "tip_product_id": False,
                "available_preset_ids": [
                    Command.create({"name": "Shared cross-company preset"})
                ],
            }
        )
        _logger.debug("Batch tip products: %s", configs.tip_product_id.ids)
        self.assertEqual(configs[0].tip_product_id, local)
        self.assertEqual(configs[1].tip_product_id, default)
        presets = self.env["pos.preset"].search(
            [("name", "=", "Shared cross-company preset")]
        )
        self.assertEqual(len(presets), 1)
        self.assertTrue(
            all(presets in config.available_preset_ids for config in configs)
        )

    def test_batch_tip_reset_preserves_shared_many2many_create(self):
        configs = self.config | self.config.copy({"name": "Batch command peer"})
        configs.write(
            {
                "iface_tipproduct": True,
                "tip_product_id": False,
                "available_preset_ids": [
                    Command.create({"name": "Shared batch preset"})
                ],
            }
        )
        presets = self.env["pos.preset"].search([("name", "=", "Shared batch preset")])
        _logger.debug(
            "Tip reset with batch CREATE: presets=%s config presets=%s",
            presets.ids,
            configs.available_preset_ids.ids,
        )
        self.assertEqual(
            len(presets), 1, "A many2many batch CREATE must create one shared record"
        )
        self.assertTrue(
            all(presets in config.available_preset_ids for config in configs)
        )

    def test_existing_config_onchange_preserves_current_session(self):
        session = self._create_session()
        onchange = self.env["pos.config"].new({}, origin=self.config)
        _logger.debug(
            "Existing config onchange: sessions=%s current=%s",
            onchange.session_ids,
            onchange.current_session_id,
        )
        self.assertEqual(onchange.current_session_id._origin, session)
        onchange.session_ids.rescue = True
        self.assertFalse(onchange.current_session_id)
        self.assertEqual(onchange.number_of_rescue_session, 1)
        self.assertFalse(session.rescue)

    def test_unsaved_config_keeps_unsaved_open_sessions(self):
        config = self.env["pos.config"].new(
            {
                "name": "Unsaved sessions",
                "session_ids": [
                    Command.create({"state": "closed"}),
                    Command.create({"state": "opened", "rescue": True}),
                    Command.create({"state": "opening_control", "rescue": False}),
                ],
            }
        )
        _logger.debug("Unsaved config session selection: %s", config.current_session_id)
        self.assertEqual(config.current_session_id, config.session_ids[-1])
        self.assertEqual(config.current_session_state, "opening_control")
        self.assertEqual(config.number_of_rescue_session, 1)
        self.assertTrue(config.has_active_session)

    def test_cached_statistics_follow_refund_link_changes(self):
        session = self._create_session()
        first = self._create_order(session)
        second = self._create_order(session, 20)
        (first | second).write({"state": "paid"})
        self.assertEqual(
            self.config.statistics_for_current_session["orders"]["paid"]["count"], 2
        )
        refund = self._create_order(session, -10, first.lines)
        refund.state = "paid"
        self.assertEqual(
            self.config.statistics_for_current_session["orders"]["paid"]["count"], 1
        )

        refund.lines.refunded_orderline_id = second.lines

        self.assertEqual(
            self.config.statistics_for_current_session["orders"]["paid"]["count"], 2
        )

    def test_cached_statistics_follow_currency_format_changes(self):
        session = self._create_session()
        session.cash_register_balance_start = 42
        self.assertIn(
            "42", self.config.statistics_for_current_session["cash"]["opening_cash"]
        )

        self.config.currency_id.symbol = "CHALLENGE"

        self.assertIn(
            "CHALLENGE",
            self.config.statistics_for_current_session["cash"]["opening_cash"],
        )
        self.assertEqual(session.cash_register_balance_start, 42)

    def test_profile_timezones_do_not_share_cached_dates(self):
        instant = fields.Datetime.to_datetime("2026-01-01 02:00:00")
        session = self._create_session(start_at=instant)
        self.env.user.tz = "UTC"
        other = self.env.user.copy(
            {"login": "config_challenge_honolulu", "tz": "Pacific/Honolulu"}
        )
        utc_config = self.config.with_context(tz=False)
        local_config = utc_config.with_user(other)
        self.assertEqual(
            utc_config.statistics_for_current_session["date"]["start_date"], "Jan 01"
        )
        self.assertEqual(
            local_config.statistics_for_current_session["date"]["start_date"], "Dec 31"
        )

        session.write({"state": "closed", "stop_at": instant})
        self.assertEqual(utc_config.last_session_closing_date, instant.date())
        self.assertEqual(
            local_config.last_session_closing_date, fields.Date.to_date("2025-12-31")
        )

    def test_cached_user_and_statistics_follow_rescue_and_name_changes(self):
        session = self._create_session()
        self.assertTrue(self.config.statistics_for_current_session)
        self.assertEqual(self.config.pos_session_username, session.user_id.name)
        session.user_id.name = "Renamed responsible"
        self.assertEqual(self.config.pos_session_username, "Renamed responsible")

        session.rescue = True

        self.assertFalse(self.config.statistics_for_current_session)
        self.assertFalse(self.config.current_user_id)

    def test_last_session_ties_select_the_newest_session(self):
        instant = fields.Datetime.to_datetime("2026-09-10 12:00:00")
        old = self._create_session()
        old.write(
            {
                "state": "closed",
                "stop_at": instant,
                "cash_register_balance_end_real": 11,
            }
        )
        recent = self._create_session()
        recent.write(
            {
                "state": "closed",
                "stop_at": instant,
                "cash_register_balance_end_real": 22,
            }
        )
        _logger.debug(
            "tied sessions old=%s recent=%s stop=%s", old.id, recent.id, instant
        )

        self.assertEqual(self.config.last_session_closing_cash, 22)

    def test_last_session_refreshes_after_correction_and_deletion(self):
        old = self._create_session()
        old.write(
            {
                "state": "closed",
                "stop_at": "2026-09-10 12:00:00",
                "cash_register_balance_end_real": 11,
            }
        )
        recent = self._create_session()
        recent.write(
            {
                "state": "closed",
                "stop_at": "2026-09-11 12:00:00",
                "cash_register_balance_end_real": 22,
            }
        )
        self.assertEqual(self.config.last_session_closing_cash, 22)
        recent.stop_at = "2026-09-09 12:00:00"
        self.assertEqual(self.config.last_session_closing_cash, 11)
        old.cash_register_balance_end_real = 33
        self.assertEqual(self.config.last_session_closing_cash, 33)
        old.unlink()
        self.assertEqual(self.config.last_session_closing_cash, 22)
        recent.unlink()
        self.assertFalse(self.config.last_session_closing_date)
        self.assertEqual(self.config.last_session_closing_cash, 0)

    def test_reordered_settings_links_are_not_a_payment_method_change(self):
        self._create_session()
        methods = self.config.payment_method_ids
        self.assertGreater(len(methods), 1)

        self.config.with_context(from_settings_view=True).write(
            {
                "payment_method_ids": [
                    Command.link(method.id) for method in reversed(methods)
                ],
            }
        )

        self.assertEqual(set(self.config.payment_method_ids.ids), set(methods.ids))

    def test_forbidden_settings_update_does_not_write_before_rejection(self):
        self._create_session()
        method = self.config.payment_method_ids[0]
        original_name = method.name
        values = {
            "payment_method_ids": [
                Command.link(pm.id) for pm in self.config.payment_method_ids
            ]
            + [Command.update(method.id, {"name": "Must never be written"})]
        }

        # Avoid TransactionCase.assertRaises' savepoint: rollback could hide an early write.
        with unittest.TestCase.assertRaises(self, UserError):
            self.config.with_context(from_settings_view=True).write(values)

        method.invalidate_recordset()
        self.assertEqual(method.name, original_name)

    def test_session_guard_rejects_a_batch_with_one_open_config(self):
        second = self.config.copy({"name": "Closed config"})
        self._create_session(rescue=True)
        with self.assertRaises(UserError):
            (second | self.config).write({"active": False})
        self.assertTrue(second.active)
        self.assertTrue(self.config.active)

    def test_session_guard_costs_no_query_for_unrestricted_keys(self):
        self._create_session()
        with self.assertQueryCount(0):
            self.config._check_session_forbidden_changes({"name": "Rename"})
        with self.assertRaises(UserError):
            self.config._check_session_forbidden_changes({"active": False})

    def test_printer_menu_remains_visible_for_other_configs(self):
        first = self.config.copy({"name": "Printer A", "is_order_printer": True})
        second = self.config.copy({"name": "Printer B", "is_order_printer": True})
        menu = self.env.ref("point_of_sale.menu_pos_preparation_printer")
        self.assertIn(menu.id, self.env["ir.ui.menu"].load_menus(False))
        first.action_archive()
        self.assertTrue(menu.active)
        second.unlink()
        self.assertFalse(menu.active)
        self.assertNotIn(menu.id, self.env["ir.ui.menu"].load_menus(False))
        first.with_context(active_test=False).action_unarchive()
        self.assertTrue(menu.active)
        self.assertIn(menu.id, self.env["ir.ui.menu"].load_menus(False))

    def test_cash_reference_cannot_reintroduce_a_parent_payment_method(self):
        branch = self.env["res.company"].create(
            {"name": "Cash reference branch", "parent_id": self.config.company_id.id}
        )
        ref = "point_of_sale.challenge_parent_cash"
        self.env["ir.model.data"]._update_xmlids(
            [{"xml_id": ref, "record": self.cash_pm1, "noupdate": True}]
        )
        config = self.config.with_context(
            allowed_company_ids=[branch.id, self.config.company_id.id]
        )

        _journal, method_ids = config._create_journal_and_payment_methods(cash_ref=ref)

        self.assertEqual(
            self.env["pos.payment.method"].browse(method_ids).company_id, branch
        )
        self.assertEqual(self.env.ref(ref), self.cash_pm1)
        local_ref = config._get_suffixed_ref_name(ref)
        self.assertEqual(self.env.ref(local_ref).company_id, branch)
        _journal, repeated_ids = config._create_journal_and_payment_methods(
            cash_ref=ref
        )
        self.assertEqual(set(repeated_ids), set(method_ids))

    def test_misowned_company_cash_reference_is_rejected(self):
        branch = self.env["res.company"].create(
            {
                "name": "Misowned reference branch",
                "parent_id": self.config.company_id.id,
            }
        )
        config = self.config.with_context(
            allowed_company_ids=[branch.id, self.config.company_id.id]
        )
        ref = "point_of_sale.challenge_misowned_cash"
        self.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": config._get_suffixed_ref_name(ref),
                    "record": self.cash_pm1,
                    "noupdate": True,
                }
            ]
        )

        with self.assertRaisesRegex(UserError, "must belong to the current company"):
            config._create_journal_and_payment_methods(cash_ref=ref)

    def test_branch_can_open_a_session_with_provisioned_methods(self):
        parent = self.env["res.company"].create(
            {"name": "Provisioning parent", "country_id": self.env.ref("base.us").id}
        )
        self.env["account.chart.template"].try_loading(
            "generic_coa", company=parent, install_demo=False
        )
        self.assertEqual(parent.chart_template, "generic_coa")
        self.env["pos.config"].with_company(
            parent
        )._create_journal_and_payment_methods()
        branch = self.env["res.company"].create(
            {
                "name": "End-to-end branch",
                "parent_id": parent.id,
                "country_id": parent.country_id.id,
            }
        )
        Config = self.env["pos.config"].with_context(
            allowed_company_ids=[branch.id, parent.id]
        )
        journal, method_ids = Config._create_journal_and_payment_methods()
        config = Config.create(
            {
                "name": "Branch shop",
                "company_id": branch.id,
                "journal_id": journal.id,
                "payment_method_ids": [Command.set(method_ids)],
            }
        )

        self.assertTrue(config.company_has_template)
        action = config.open_ui()

        self.assertEqual(config.current_session_id.company_id, branch)
        self.assertEqual(config.payment_method_ids.company_id, branch)
        self.assertIn(f"/pos/ui/{config.id}", action["url"])

    def test_unsaved_config_has_empty_dashboard_values(self):
        config = self.env["pos.config"].new({"name": "Unsaved"})
        self.assertFalse(config.current_session_id)
        self.assertFalse(config.current_user_id)
        self.assertFalse(config.statistics_for_current_session)
        self.assertFalse(config.last_session_closing_date)
        self.assertEqual(config.last_session_closing_cash, 0)

    def test_payment_bypass_does_not_bypass_archiving(self):
        method = self.bank_pm1.copy({"name": "Extra bank"})
        self._create_session()
        config = self.config.with_context(
            bypass_payment_method_ids_forbidden_change=True
        )
        config.write({"payment_method_ids": [Command.link(method.id)]})
        self.assertIn(method, config.payment_method_ids)
        with self.assertRaises(UserError):
            config.action_archive()

    def test_pos_manager_guard_and_settings_write(self):
        manager = self.env["res.users"].create(
            {
                "name": "Challenge POS manager",
                "login": "config_challenge_manager",
                "company_id": self.config.company_id.id,
                "company_ids": [Command.set(self.config.company_id.ids)],
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("point_of_sale.group_pos_manager").id,
                        ]
                    )
                ],
            }
        )
        self._create_session()
        config = self.config.with_user(manager)
        config.write({"name": "Manager rename"})
        self.assertEqual(config.name, "Manager rename")
        with self.assertRaises(UserError):
            config.action_archive()

    def test_sequence_fallback_and_duplicate_company_priority(self):
        Sequence = self.env["ir.sequence"].sudo()
        Sequence.search([("code", "=", "pos.session")]).unlink()
        self.assertEqual(self.config._get_next_session_name(), "/")
        shared = Sequence.create(
            {
                "name": "Shared",
                "code": "pos.session",
                "company_id": False,
                "prefix": "GLOBAL/",
            }
        )
        self.assertEqual(self.config._get_next_session_name(), "GLOBAL/1")
        first = Sequence.create(
            {
                "name": "First",
                "code": "pos.session",
                "company_id": self.config.company_id.id,
                "prefix": "FIRST/",
            }
        )
        second = first.copy({"name": "Second", "prefix": "SECOND/"})

        self.assertEqual(self.config._get_next_session_name(), "FIRST/1")

        self.assertEqual(first.number_next_actual, 2)
        self.assertEqual(second.number_next_actual, 1)
        self.assertEqual(shared.number_next_actual, 2)
