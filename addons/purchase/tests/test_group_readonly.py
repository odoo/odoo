from lxml import etree

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "fast")
class TestPurchaseReadonlyGroup(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.group_readonly = cls.env.ref("purchase.group_purchase_readonly")

    def test_group_configuration(self) -> None:
        self.assertTrue(self.group_readonly)
        self.assertEqual(self.group_readonly.name, "Read-only")

        privilege = self.env.ref("purchase.res_groups_privilege_purchase")
        self.assertEqual(self.group_readonly.privilege_id, privilege)

        base_user = self.env.ref("base.group_user")
        self.assertIn(base_user, self.group_readonly.implied_ids)

    REQUIRED_MODELS = (
        "purchase.order",
        "purchase.order.line",
        "purchase.report",
        "vendor.delay.report",
        "stock.picking",
        "stock.move",
        "mrp.production",
    )

    BRIDGE_OF = {
        "vendor.delay.report": "purchase_stock",
        "stock.picking": "purchase_stock",
        "stock.move": "purchase_stock",
        "mrp.production": "purchase_mrp",
    }

    def test_acl_configuration(self) -> None:
        acls = self.env["ir.access"].search(
            [("group_id", "=", self.group_readonly.id), ("kind", "=", "permission")]
        )

        granted = set(acls.mapped("model_id.model"))
        installed = set(
            self.env["ir.module.module"]
            .search([("state", "=", "installed")])
            .mapped("name")
        )
        for model in self.REQUIRED_MODELS:
            if self.BRIDGE_OF.get(model, "purchase") not in installed:
                continue
            with self.subTest(model=model):
                self.assertIn(
                    model,
                    granted,
                    f"the readonly group must be able to read {model}",
                )

        for acl in acls:
            self.assertTrue(acl.for_read, f"ACL {acl.name} should allow read")
            self.assertFalse(acl.for_write, f"ACL {acl.name} should block write")
            self.assertFalse(acl.for_create, f"ACL {acl.name} should block create")
            self.assertFalse(acl.for_unlink, f"ACL {acl.name} should block unlink")

    def test_the_all_documents_rung_implies_readonly(self) -> None:
        user_all = self.env.ref("purchase.group_purchase_user_all")
        user_own = self.env.ref("purchase.group_purchase_user")
        manager = self.env.ref("purchase.group_purchase_manager")
        self.assertIn(self.group_readonly, user_all.implied_ids)
        self.assertIn(self.group_readonly, manager.all_implied_ids)
        self.assertNotIn(self.group_readonly, user_own.all_implied_ids)


@tagged("post_install", "-at_install", "fast")
class TestPurchaseReadonlyPermissions(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.group_readonly = cls.env.ref("purchase.group_purchase_readonly")

        cls.readonly_user = cls.env["res.users"].create(
            {
                "name": "Test Readonly",
                "login": "test_po_readonly",
                "group_ids": [Command.set([cls.group_readonly.id])],
            }
        )

        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Vendor", "supplier_rank": 1}
        )

        cls.purchase_order = cls.env["purchase.order"].create(
            {"partner_id": cls.partner.id}
        )

    IMPLIED_READ_MODELS = (
        "account.account",
        "account.account.tag",
        "account.analytic.account",
        "account.fiscal.position",
        "account.payment.term",
        "account.tax",
        "account.tax.group",
        "product.category",
        "product.pricelist",
        "product.product",
        "product.supplierinfo",
        "product.template",
        "project.project",
        "project.task",
        "res.company",
        "res.currency",
        "res.partner",
        "stock.location",
        "stock.move.line",
        "stock.picking.type",
        "stock.quant",
        "stock.rule",
        "stock.warehouse",
        "uom.uom",
    )

    def test_implied_models_stay_readable(self) -> None:
        for model in self.IMPLIED_READ_MODELS:
            if model not in self.env:
                continue
            with self.subTest(model=model):
                self.env[model].with_user(self.readonly_user).check_access("read")

    def test_read_allowed(self) -> None:
        env_user = self.env(user=self.readonly_user)

        orders = env_user["purchase.order"].search([])
        self.assertGreaterEqual(len(orders), 1)

        env_user["purchase.order.line"].search([])

    def test_write_blocked(self) -> None:
        env_user = self.env(user=self.readonly_user)
        order = env_user["purchase.order"].browse(self.purchase_order.id)

        with self.assertRaises(AccessError):
            order.write({"notes": "Test"})

    def test_create_blocked(self) -> None:
        env_user = self.env(user=self.readonly_user)

        with self.assertRaises(AccessError):
            env_user["purchase.order"].create({"partner_id": self.partner.id})

    def test_unlink_blocked(self) -> None:
        env_user = self.env(user=self.readonly_user)
        order = env_user["purchase.order"].browse(self.purchase_order.id)

        with self.assertRaises(AccessError):
            order.unlink()

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
            "purchase.view_purchase_order_form",
            "purchase.order",
            "purchase.group_purchase_user",
            (
                "action_send_rfq",
                "action_confirm",
                "action_acknowledge",
                "action_cancel",
                "action_draft",
            ),
            self.readonly_user,
        )


@tagged("post_install", "-at_install", "fast")
class TestPurchaseReadonlyMenus(TransactionCase):
    GATED_IN_CORE = (
        "purchase.menu_purchase_root",
        "purchase.menu_purchase_reporting",
        "purchase.menu_purchase_report",
    )
    UNGROUPED_IN_CORE = (
        "purchase.menu_purchase_rfq",
        "purchase.menu_purchase_form_action",
        "purchase.menu_procurement_management_supplier_name",
        "purchase.menu_purchase_products",
        "purchase.menu_procurement_partner_contact_form",
        "purchase.menu_product_pricelist_action2_purchase",
    )

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.group_readonly = cls.env.ref("purchase.group_purchase_readonly")
        cls.purchase_user = cls.env["res.users"].create(
            {
                "name": "Test Purchase User",
                "login": "test_po_user_menus",
                "group_ids": [
                    Command.set([cls.env.ref("purchase.group_purchase_user").id])
                ],
            }
        )

    def test_gated_menus_include_readonly_group(self) -> None:
        for xmlid in self.GATED_IN_CORE:
            with self.subTest(menu=xmlid):
                self.assertIn(
                    self.group_readonly,
                    self.env.ref(xmlid).group_ids,
                    f"{xmlid} is gated in core, so the readonly group must be added",
                )

    def test_purchase_user_keeps_the_ungrouped_menus(self) -> None:
        visible = (
            self.env["ir.ui.menu"].with_user(self.purchase_user)._get_visible_menu_ids()
        )

        for xmlid in self.UNGROUPED_IN_CORE:
            menu = self.env.ref(xmlid)
            with self.subTest(menu=xmlid):
                self.assertNotIn(
                    self.group_readonly,
                    menu.group_ids,
                    f"{xmlid} is ungrouped in core, so granting a group hides it "
                    f"from every other purchase user",
                )
                if menu.active:
                    self.assertIn(
                        menu.id,
                        visible,
                        f"a purchase user must still reach {xmlid}",
                    )


@tagged("post_install", "-at_install", "fast")
class TestPurchaseReadonlyRecordRules(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.group_readonly = cls.env.ref("purchase.group_purchase_readonly")
        group_user = cls.env.ref("purchase.group_purchase_user")

        cls.buyer = cls.env["res.users"].create(
            {
                "name": "Test Buyer",
                "login": "test_po_buyer",
                "group_ids": [Command.set([group_user.id])],
            }
        )
        cls.buyer_with_readonly = cls.env["res.users"].create(
            {
                "name": "Test Buyer Readonly",
                "login": "test_po_buyer_readonly",
                "group_ids": [Command.set([group_user.id, cls.group_readonly.id])],
            }
        )
        cls.readonly_user = cls.env["res.users"].create(
            {
                "name": "Test Readonly Only",
                "login": "test_po_readonly_only",
                "group_ids": [Command.set([cls.group_readonly.id])],
            }
        )

        partner = cls.env["res.partner"].create(
            {"name": "Test Rule Vendor", "supplier_rank": 1}
        )
        cls.other_order = cls.env["purchase.order"].create(
            {"partner_id": partner.id, "user_id": cls.env.ref("base.user_admin").id}
        )

    def test_buyer_cannot_read_another_buyers_order(self) -> None:
        with self.assertRaises(AccessError):
            self.other_order.with_user(self.buyer).read(["id"])

    def test_readonly_is_a_decision_to_see_every_order(self) -> None:
        self.other_order.with_user(self.buyer_with_readonly).read(["id"])
        with self.assertRaises(AccessError):
            self.other_order.with_user(self.buyer_with_readonly).write({"notes": "x"})

    def test_readonly_only_user_reads_every_order(self) -> None:
        self.other_order.with_user(self.readonly_user).read(["id"])
