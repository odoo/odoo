from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

READ_VIA_BASE_GROUP_USER = [
    "product.attribute",
    "product.attribute.value",
    "product.category",
    "product.product",
    "product.template",
    "product.template.attribute.line",
    "product.template.attribute.value",
    "res.company",
    "res.partner",
    "stock.location",
    "stock.move.line",
    "stock.picking.type",
    "stock.quant",
    "stock.warehouse",
    "uom.uom",
]


@tagged("post_install", "-at_install")
class TestMrpGroupReadonly(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_readonly = cls.env.ref("mrp.group_mrp_readonly")

        cls.user_readonly = cls.env["res.users"].create(
            {
                "name": "Test MRP Readonly User",
                "login": "test_mrp_readonly",
                "email": "test_mrp_readonly@test.com",
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.group_readonly.id,
                        ]
                    )
                ],
            }
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product MRP Readonly",
                "type": "consu",
            }
        )

        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product.product_tmpl_id.id,
                "product_qty": 1.0,
            }
        )

        cls.production = cls.env["mrp.production"].create(
            {
                "product_id": cls.product.id,
                "product_qty": 1.0,
                "bom_id": cls.bom.id,
            }
        )

    def test_group_exists(self):
        self.assertTrue(self.group_readonly, "Group mrp_readonly should exist")
        self.assertEqual(
            self.group_readonly.name,
            "Read-only",
            "Group name should be 'Read-only'",
        )

    def test_group_privilege_hierarchy(self):
        privilege = self.env.ref("mrp.res_groups_privilege_manufacturing")
        self.assertEqual(
            self.group_readonly.privilege_id,
            privilege,
            "Readonly group should belong to the Manufacturing privilege",
        )

        group_user = self.env.ref("mrp.group_mrp_user")
        self.assertLess(
            self.group_readonly.sequence,
            group_user.sequence,
            "Readonly sequence should be lower than User sequence",
        )

    def test_readonly_is_implied_by_the_user_tier(self):
        group_user = self.env.ref("mrp.group_mrp_user")
        group_manager = self.env.ref("mrp.group_mrp_manager")
        self.assertIn(
            self.group_readonly,
            group_user.implied_ids,
            "the User tier must imply Read-only, or the readonly group cannot "
            "be used as a positive gate",
        )
        self.assertIn(self.group_readonly, group_manager.all_implied_ids)

    def test_no_acl_row_targets_a_transient_model(self):
        rows = self.env["ir.access"].search(
            [("group_id", "=", self.group_readonly.id), ("kind", "=", "permission")]
        )
        self.assertTrue(rows)
        transient = [
            row.model_id.model
            for row in rows
            if self.env[row.model_id.model]._transient
        ]
        self.assertFalse(
            transient,
            f"read rows on transient models never apply: {sorted(transient)}",
        )

    def test_no_server_action_reaches_readonly(self):
        actions = self.env["ir.actions.server"].search(
            [("group_ids", "in", self.group_readonly.ids)]
        )
        self.assertFalse(
            actions,
            "server actions reach the readonly tier: %s"
            % sorted(actions.mapped("name")),
        )

    def test_models_read_through_base_group_user_stay_readable(self):
        access = self.env["ir.model.access"].with_user(self.user_readonly)
        lost = [
            model
            for model in READ_VIA_BASE_GROUP_USER
            if not access.check(model, "read", False)
        ]
        self.assertFalse(lost, "the readonly tier lost read on: %s" % lost)

    def test_readonly_user_can_read_bom(self):
        bom = self.bom.with_user(self.user_readonly)
        bom.read(["product_tmpl_id", "product_qty"])

    def test_readonly_user_cannot_create_bom(self):
        bom_model = self.env["mrp.bom"].with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            bom_model.create(
                {
                    "product_tmpl_id": self.product.product_tmpl_id.id,
                    "product_qty": 1.0,
                }
            )

    def test_readonly_user_cannot_write_bom(self):
        bom = self.bom.with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            bom.write({"product_qty": 2.0})

    def test_readonly_user_cannot_unlink_bom(self):
        bom = self.bom.with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            bom.unlink()

    def test_readonly_user_can_read_production(self):
        production = self.production.with_user(self.user_readonly)
        production.read(["product_id", "product_qty", "state"])

    def test_readonly_user_cannot_write_production(self):
        production = self.production.with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            production.write({"product_qty": 5.0})

    def test_readonly_user_cannot_create_production(self):
        production_model = self.env["mrp.production"].with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            production_model.create(
                {
                    "product_id": self.product.id,
                    "product_qty": 1.0,
                }
            )

    def test_readonly_user_can_read_product(self):
        product = self.product.with_user(self.user_readonly)
        product.read(["name", "type"])

    def test_readonly_user_cannot_write_product(self):
        product = self.product.with_user(self.user_readonly)
        with self.assertRaises(AccessError):
            product.write({"name": "Hacked Product"})

    def test_readonly_user_can_read_stock_models(self):
        user = self.user_readonly
        models_and_fields = [
            ("stock.warehouse", ["name", "code"]),
            ("stock.location", ["name", "usage"]),
            ("stock.picking.type", ["name", "code"]),
        ]
        for model_name, field_list in models_and_fields:
            with self.subTest(model=model_name):
                records = self.env[model_name].with_user(user).search([], limit=1)
                self.assertTrue(
                    records,
                    f"Should find at least one {model_name} record",
                )
                records.read(field_list)

    def test_readonly_user_can_read_partner_and_company(self):
        user = self.user_readonly

        partner = self.env["res.partner"].with_user(user).search([], limit=1)
        self.assertTrue(partner)
        partner.read(["name"])

        company = self.env["res.company"].with_user(user).search([], limit=1)
        self.assertTrue(company)
        company.read(["name"])

    def test_readonly_user_can_read_uom(self):
        uom = self.env["uom.uom"].with_user(self.user_readonly).search([], limit=1)
        self.assertTrue(uom)
        uom.read(["name"])

    def test_readonly_user_cannot_write_stock_models(self):
        user = self.user_readonly
        models_to_test = [
            "stock.warehouse",
            "stock.location",
            "stock.picking.type",
        ]
        for model_name in models_to_test:
            with self.subTest(model=model_name):
                record = self.env[model_name].with_user(user).search([], limit=1)
                if record:
                    with self.assertRaises(AccessError):
                        record.write({"name": "Hacked"})

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

    def test_production_write_buttons_are_hidden_from_readonly(self):
        self._assert_write_buttons_gated(
            "mrp.mrp_production_form_view",
            "mrp.production",
            "mrp.group_mrp_user",
            (
                "button_mark_done",
                "action_confirm",
                "button_plan",
                "button_unplan",
                "action_start",
                "action_assign",
                "action_unreserve",
                "action_cancel",
                "button_unbuild",
            ),
            self.user_readonly,
        )
