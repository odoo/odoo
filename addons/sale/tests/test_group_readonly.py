from lxml import etree

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests.common import TransactionCase, tagged

CORE_GROUP_PER_GRANTED_MENU = {
    "sale.menu_sale_quotations": "sale.group_sale_salesman",
    "sale.menu_sale_order": "sale.group_sale_salesman",
    "sale.res_partner_menu": "sale.group_sale_salesman",
    "sale.product_menu_catalog": "sale.group_sale_salesman",
    "sale.menu_sale_report": "sale.group_sale_manager",
}

FEATURE_FLAG_MENUS = {
    "sale.menu_products": "product.group_product_variant",
    "sale.menu_product_pricelist_main": "product.group_product_pricelist",
}

MENUS_THE_ROLE_MAY_SEE_ALONE = {
    "sale.menu_sale_report",
    "account.menu_action_account_payments_receivable",
    "account.menu_action_account_payments_payable",
}


@tagged("post_install", "-at_install")
class TestSaleGroupReadonly(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.group_readonly = cls.env.ref("sale.group_sale_readonly")

        cls.user_readonly = cls.env["res.users"].create(
            {
                "name": "Test Sale Readonly User",
                "login": "test_sale_readonly",
                "email": "test_sale_readonly@test.com",
                "group_ids": [Command.set([cls.group_readonly.id])],
            }
        )

        cls.user_salesman = cls.env["res.users"].create(
            {
                "name": "Test Sale Salesman",
                "login": "test_sale_salesman",
                "email": "test_sale_salesman@test.com",
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("sale.group_sale_salesman").id,
                        ]
                    )
                ],
            }
        )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Customer",
            }
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 100.0,
            }
        )

        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "user_id": cls.user_salesman.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )

    def test_group_is_a_role_under_the_sales_privilege(self) -> None:
        self.assertEqual(
            self.group_readonly.privilege_id,
            self.env.ref("sale.res_groups_privilege_sales"),
            "the role must sit under the Sales privilege",
        )
        self.assertIn(
            self.env.ref("base.group_user"),
            self.group_readonly.all_implied_ids,
            "the group must imply base.group_user (sale/security/res_groups.xml)",
        )

    def test_readonly_user_is_an_internal_user(self) -> None:
        self.assertIn(
            self.env.ref("base.group_user"),
            self.user_readonly.all_group_ids,
            "holding only the role must still grant base.group_user",
        )

    def test_readonly_user_can_read_sale_order(self) -> None:
        order = self.sale_order.with_user(self.user_readonly)
        order.read(["partner_id", "amount_total"])

    def test_readonly_user_cannot_create_sale_order(self) -> None:
        sale_order_env = self.env["sale.order"].with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            sale_order_env.create(
                {
                    "partner_id": self.partner.id,
                }
            )

    def test_readonly_user_cannot_write_sale_order(self) -> None:
        order = self.sale_order.with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            order.write({"client_order_ref": "Test ref"})

    def test_readonly_user_cannot_unlink_sale_order(self) -> None:
        order = self.sale_order.with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            order.unlink()

    def test_readonly_user_can_read_order_lines(self) -> None:
        lines = self.sale_order.line_ids.with_user(self.user_readonly)
        lines.read(["product_id", "product_uom_qty", "price_unit"])

    def test_the_all_documents_rung_implies_readonly(self) -> None:
        all_documents = self.env.ref("sale.group_sale_salesman_all_leads")
        salesman = self.env.ref("sale.group_sale_salesman")
        manager = self.env.ref("sale.group_sale_manager")
        self.assertIn(self.group_readonly, all_documents.implied_ids)
        self.assertIn(self.group_readonly, manager.all_implied_ids)
        self.assertNotIn(self.group_readonly, salesman.all_implied_ids)

    def test_readonly_reads_every_order_whatever_else_it_holds(self) -> None:
        other_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "user_id": self.env.ref("base.user_admin").id,
            }
        )
        with self.assertRaises(AccessError):
            other_order.with_user(self.user_salesman).read(["id"])
        self.user_salesman.write({"group_ids": [Command.link(self.group_readonly.id)]})
        other_order.with_user(self.user_salesman).read(["id"])
        with self.assertRaises(AccessError):
            other_order.with_user(self.user_salesman).write({"client_order_ref": "x"})
        other_order.with_user(self.user_readonly).read(["id"])

    def test_salesman_can_read_sale_order(self) -> None:
        order = self.sale_order.with_user(self.user_salesman)
        order.read(["partner_id", "amount_total"])

    def test_salesman_can_write_sale_order(self) -> None:
        order = self.sale_order.with_user(self.user_salesman)
        order.write({"client_order_ref": "Regression test ref"})

    def test_granted_menus_are_visible_to_the_role(self) -> None:
        visible = (
            self.env["ir.ui.menu"].with_user(self.user_readonly)._get_visible_menu_ids()
        )
        for xmlid in CORE_GROUP_PER_GRANTED_MENU:
            menu = self.env.ref(xmlid)
            if not menu.active:
                continue
            self.assertIn(
                menu.id,
                visible,
                f"{xmlid} is granted but the role cannot see it",
            )

    def test_menu_grants_do_not_displace_the_core_group(self) -> None:
        for xmlid, core_group_xmlid in CORE_GROUP_PER_GRANTED_MENU.items():
            group_ids = self.env.ref(xmlid).group_ids
            self.assertIn(
                self.env.ref(core_group_xmlid),
                group_ids,
                f"{xmlid} lost its core group {core_group_xmlid}",
            )
            self.assertIn(self.group_readonly, group_ids, f"{xmlid} lost the role")

    def test_feature_flag_menus_stay_behind_their_flag(self) -> None:
        visible = (
            self.env["ir.ui.menu"].with_user(self.user_readonly)._get_visible_menu_ids()
        )
        group_user = self.env.ref("base.group_user")
        for xmlid, flag_xmlid in FEATURE_FLAG_MENUS.items():
            flag = self.env.ref(flag_xmlid)
            flag_is_on = flag in group_user.all_implied_ids
            self.assertEqual(
                flag in self.user_readonly.all_group_ids,
                flag_is_on,
                f"the role must hold the feature flag {flag_xmlid} only through "
                "base.group_user",
            )
            menu = self.env.ref(xmlid)
            self.assertEqual(
                menu.id in visible,
                flag_is_on and menu.active,
                f"{xmlid} must follow the flag {flag_xmlid}, not the role",
            )

    def test_role_outranks_a_salesperson_only_where_intended(self) -> None:
        menu_model = self.env["ir.ui.menu"]
        visible_readonly = menu_model.with_user(
            self.user_readonly
        )._get_visible_menu_ids()
        visible_salesman = menu_model.with_user(
            self.user_salesman
        )._get_visible_menu_ids()
        allowed_roots = [
            menu.id
            for menu in (
                self.env.ref(xmlid, raise_if_not_found=False)
                for xmlid in MENUS_THE_ROLE_MAY_SEE_ALONE
            )
            if menu
        ]
        allowed = set(menu_model.search([("id", "child_of", allowed_roots)]).ids)
        unexpected = sorted(
            menu_model.browse(menu_id).complete_name
            for menu_id in set(visible_readonly) - set(visible_salesman) - allowed
        )
        self.assertFalse(
            unexpected,
            f"the role sees menus a salesperson cannot, and nobody decided to: "
            f"{unexpected}",
        )

    def test_every_acl_row_grants_something(self) -> None:
        group_user = self.env.ref("base.group_user")
        access = self.env["ir.model.access"]
        module_model = self.env["ir.module.module"]
        closures = {}
        dead = []
        for row in self._tier_acl_rows():
            row_module = row.get_external_id()[row.id].split(".")[0]
            if row_module not in closures:
                module = module_model.search([("name", "=", row_module)])
                closures[row_module] = {row_module} | set(
                    module.upstream_dependencies(
                        exclude_states=("uninstalled", "uninstallable", "to remove")
                    ).mapped("name")
                )
            granting = access.search(
                [
                    ("model_id", "=", row.model_id.id),
                    ("group_id", "=", group_user.id),
                    ("perm_read", "=", True),
                ]
            )
            granting_modules = {
                xmlid.split(".")[0] for xmlid in granting.get_external_id().values()
            }
            if granting_modules & closures[row_module]:
                dead.append(row.model_id.model)
        self.assertFalse(
            dead, f"these rows grant nothing over base.group_user: {sorted(dead)}"
        )

    def test_no_acl_row_targets_a_transient_model(self) -> None:
        transient = [
            row.model_id.model
            for row in self._tier_acl_rows()
            if self.env[row.model_id.model]._transient
        ]
        self.assertFalse(
            transient,
            f"read rows on transient models never apply: {sorted(transient)}",
        )

    def test_acl_rows_grant_read_only(self) -> None:
        writable = [
            row.model_id.model
            for row in self._tier_acl_rows()
            if row.perm_write or row.perm_create or row.perm_unlink
        ]
        self.assertFalse(writable, f"these rows are not read-only: {sorted(writable)}")

    def _tier_acl_rows(self):
        rows = self.env["ir.model.access"].search(
            [("group_id", "=", self.group_readonly.id)]
        )
        self.assertTrue(rows, "the tier must grant something")
        return rows

    def _assert_write_buttons_gated(
        self, view_xmlid, model, rung, buttons, user, feature_flags=()
    ):
        view = self.env.ref(view_xmlid)
        arch = etree.fromstring(view.arch)
        for button in buttons:
            nodes = arch.xpath(f"//header/button[@name='{button}']")
            self.assertTrue(nodes, f"{button} is not in {view_xmlid}")
            for node in nodes:
                if node.get("groups") in feature_flags:
                    continue
                self.assertEqual(node.get("groups"), rung, button)
        views = self.env[model].with_user(user).get_views([(view.id, "form")])
        rendered = views["views"]["form"]["arch"]
        for button in buttons:
            self.assertNotIn(f'name="{button}"', rendered, button)

    def test_order_write_buttons_are_hidden_from_readonly(self) -> None:
        self._assert_write_buttons_gated(
            "sale.view_sale_order_form",
            "sale.order",
            "sale.group_sale_salesman",
            (
                "action_send_quotation",
                "action_confirm",
                "payment_action_capture",
                "payment_action_void",
                "action_cancel",
                "action_draft",
            ),
            self.user_readonly,
            feature_flags=("sale.group_proforma_sales",),
        )
