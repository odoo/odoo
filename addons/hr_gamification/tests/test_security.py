from odoo.tests import common, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


class TestSecurity(common.TransactionCase):
    ALLOWED_GROUPS = (
        "gamification.group_gamification_user",
        "gamification.group_gamification_manager",
        "hr.group_hr_user",
    )

    def _module_acls(self):
        xmlids = self.env["ir.model.data"].search(
            [("module", "=", "hr_gamification"), ("model", "=", "ir.model.access")]
        )
        return self.env["ir.model.access"].browse(xmlids.mapped("res_id"))

    def _module_rules(self):
        xmlids = self.env["ir.model.data"].search(
            [("module", "=", "hr_gamification"), ("model", "=", "ir.rule")]
        )
        return self.env["ir.rule"].browse(xmlids.mapped("res_id"))

    def test_no_acl_or_rule_still_points_at_base_group_user(self):
        base_group_user = self.env.ref("base.group_user")
        allowed = {self.env.ref(xmlid) for xmlid in self.ALLOWED_GROUPS}

        acls = self._module_acls()
        for acl in acls:
            with self.subTest(acl=acl.name):
                self.assertNotEqual(acl.group_id, base_group_user)
                self.assertIn(acl.group_id, allowed)
        self.assertEqual(len(acls), 5)

        rules = self._module_rules()
        for rule in rules:
            with self.subTest(rule=rule.name):
                self.assertNotIn(base_group_user, rule.groups)
                self.assertTrue(set(rule.groups.ids) <= {g.id for g in allowed})
        self.assertEqual(len(rules), 5)


@tagged("post_install", "-at_install")
class TestMenuRemoval(common.TransactionCase):
    def test_no_gamification_menu_under_hr(self):
        manager = mail_new_test_user(
            self.env,
            login="hr_gam_menu_manager",
            name="HR Gamification Menu Manager",
            email="hr_gam_menu_mgr@example.com",
            groups="base.group_user,hr.group_hr_manager",
        )
        menus = self.env["ir.ui.menu"].with_user(manager).load_menus(False)
        loaded_ids = {key for key in menus if isinstance(key, int)}

        hr_config = self.env.ref("hr.menu_human_resources_configuration")
        self.assertIn(hr_config.id, loaded_ids)

        descendants = (
            self.env["ir.ui.menu"]
            .browse(sorted(loaded_ids))
            .filtered(
                lambda menu: (
                    menu != hr_config
                    and menu.parent_path.startswith(hr_config.parent_path)
                )
            )
        )
        self.assertTrue(descendants, "HR Configuration lost every child")
        for menu in descendants:
            with self.subTest(menu=menu.complete_name):
                res_model = getattr(menu.action, "res_model", "") or ""
                self.assertFalse(res_model.startswith("gamification."))

        self.assertFalse(
            self.env.ref(
                "hr_gamification.menu_hr_gamification", raise_if_not_found=False
            )
        )
        self.assertFalse(
            self.env["ir.model.data"].search_count(
                [("module", "=", "hr_gamification"), ("model", "=", "ir.ui.menu")]
            )
        )
