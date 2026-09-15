from odoo import exceptions

from odoo.addons.sale_team.tests.common import TestSalesCommon


class TestMembershipMultiParameter(TestSalesCommon):
    def test_parameter_string_false_is_false(self):
        ICP = self.env["ir.config_parameter"].sudo()
        for raw, expected in (
            ("False", False),
            ("0", False),
            ("off", False),
            ("True", True),
            ("1", True),
        ):
            ICP.search([("key", "=", "sale_team.membership_multi")]).unlink()
            ICP.create({"key": "sale_team.membership_multi", "value": raw})
            self.env.invalidate_all()
            self.assertEqual(
                self.env["team.team"]._is_membership_multi("sale"),
                expected,
                f"parameter {raw!r} should read as {expected}",
            )
            team = self.env["team.team"].create(
                {
                    "use_sale": True,
                    "name": f"P {raw}",
                    "company_id": False,
                }
            )
            self.assertEqual(team.is_membership_multi, expected)

    def test_parameter_absent_defaults_to_mono(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=", "sale_team.membership_multi")]
        ).unlink()
        self.env.invalidate_all()
        self.assertFalse(self.env["team.team"]._is_membership_multi("sale"))


class TestMultiMembershipActivation(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )

    def test_sales_administrator_can_activate(self):
        self.assertFalse(self.env["team.team"]._is_membership_multi("sale"))
        self.env["team.team"].with_user(
            self.user_sales_manager
        ).action_activate_multi_membership()
        self.env.invalidate_all()
        self.assertTrue(self.env["team.team"]._is_membership_multi("sale"))

    def test_salesman_cannot_activate(self):
        salesman = self.user_sales_salesman
        self.assertFalse(salesman.has_group("sale.group_sale_manager"))
        with self.assertRaises(exceptions.AccessError):
            self.env["team.team"].with_user(salesman).action_activate_multi_membership()
        self.env.invalidate_all()
        self.assertFalse(self.env["team.team"]._is_membership_multi("sale"))

    def test_activation_does_not_require_settings_rights(self):
        manager = self.user_sales_manager
        self.assertFalse(manager.has_group("base.group_system"))
        with self.assertRaises(exceptions.AccessError), self.env.cr.savepoint():
            self.env["ir.config_parameter"].with_user(manager).set_param(
                "sale_team.membership_multi", True
            )
        self.env["team.team"].with_user(manager).action_activate_multi_membership()
        self.env.invalidate_all()
        self.assertTrue(self.env["team.team"]._is_membership_multi("sale"))


class TestMembershipMultiIsInvalidatedEverywhere(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )

    def _cached_copies(self):
        return {
            name
            for name, model in self.env.registry.items()
            if (field := model._fields.get("is_membership_multi"))
            and field.compute
            and not field.store
        }

    def test_only_team_caches_the_setting(self):
        self.assertEqual(self._cached_copies(), {"team.team"})

    def test_every_cached_copy_follows_the_parameter(self):
        ICP = self.env["ir.config_parameter"].sudo()
        for expected, value in ((True, True), (False, False)):
            with self.subTest(value=value):
                ICP.set_param("sale_team.membership_multi", value)
                self.assertEqual(
                    self.env["team.team"]._is_membership_multi("sale"), expected
                )
                for name in self._cached_copies():
                    record = self.env[name].search([], limit=1)
                    if record:
                        self.assertEqual(record.is_membership_multi, expected)

    def test_unsetting_the_parameter_also_invalidates(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sale_team.membership_multi", True)
        self.assertTrue(self.sales_team_1.is_membership_multi)

        ICP.search([("key", "=", "sale_team.membership_multi")]).unlink()
        self.assertFalse(self.sales_team_1.is_membership_multi)
