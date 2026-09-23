import unittest

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


def has_publish_date_field(env):
    env.cr.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'product_template' AND column_name = 'publish_date'"
    )
    has_column = bool(env.cr.fetchone())
    has_publish_date = "publish_date" in env["product.template"]._fields
    if has_column and not has_publish_date:
        raise unittest.SkipTest(
            "publish_date NOT NULL constraint without website_sale loaded"
        )
    return has_publish_date


class BlockedLocationCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.has_publish_date = has_publish_date_field(cls.env)

        cls.Location = cls.env["stock.location"]
        cls.Quant = cls.env["stock.quant"]
        cls.Picking = cls.env["stock.picking"]
        cls.Move = cls.env["stock.move"]
        cls.MoveLine = cls.env["stock.move.line"]

        cls.product = cls._create_product("Test Product")

        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.picking_type_out = cls.env.ref("stock.picking_type_out")

        cls.soft_in_location = cls._create_location("Soft In", block_type="soft_in")
        cls.soft_out_location = cls._create_location("Soft Out", block_type="soft_out")
        cls.soft_both_location = cls._create_location(
            "Soft Both", block_type="soft_both"
        )
        cls.hard_block_location = cls._create_location("Hard", block_type="hard")
        cls.normal_location = cls._create_location("Normal")

        cls.group_force_in = cls.env.ref(
            "stock.group_force_blocked_location_in",
        )
        cls.group_force_out = cls.env.ref(
            "stock.group_force_blocked_location_out",
        )
        cls.group_hard_override = cls.env.ref(
            "stock.group_override_hard_block",
        )
        cls.group_stock_user = cls.env.ref("stock.group_stock_user")
        cls.group_stock_manager = cls.env.ref("stock.group_stock_manager")

        cls.normal_user = cls._create_user("Normal User", cls.group_stock_user)
        cls.force_in_user = cls._create_user(
            "Force In User", cls.group_stock_user, cls.group_force_in
        )
        cls.force_out_user = cls._create_user(
            "Force Out User", cls.group_stock_user, cls.group_force_out
        )
        cls.hard_override_user = cls._create_user(
            "Hard Override User",
            cls.group_stock_user,
            cls.group_stock_manager,
            cls.group_hard_override,
        )
        cls.manager_user = cls._create_user("Stock Manager", cls.group_stock_manager)

        cls.vendor_group = cls.env["res.groups"].create(
            {"name": "Test Vendor (no stock group)"},
        )
        for model_xmlid in (
            "stock.model_stock_quant",
            "stock.model_stock_move",
            "stock.model_stock_move_line",
            "stock.model_stock_location",
            "product.model_product_product",
            "product.model_product_template",
            "mrp.model_mrp_bom",
            "mrp.model_mrp_bom_line",
            "mrp.model_mrp_bom_byproduct",
        ):
            model = cls.env.ref(model_xmlid, raise_if_not_found=False)
            if not model:
                continue
            cls.env["ir.access"].create(
                {
                    "name": f"vendor_test_{model_xmlid}",
                    "model_id": model.id,
                    "group_id": cls.vendor_group.id,
                    "kind": "permission",
                    "operation": "r",
                },
            )
        cls.vendor_user = cls._create_user(
            "Vendor User", cls.env.ref("base.group_user"), cls.vendor_group
        )

    @classmethod
    def _create_product(cls, name):
        vals = {"name": name, "type": "consu", "is_storable": True}
        if cls.has_publish_date:
            vals["publish_date"] = fields.Datetime.now()
        return cls.env["product.template"].create(vals).product_variant_ids[:1]

    @classmethod
    def _create_location(cls, name, block_type="none", parent=None):
        return cls.env["stock.location"].create(
            {
                "name": name,
                "location_id": (parent or cls.env.ref("stock.stock_location_stock")).id,
                "block_type": block_type,
            },
        )

    @classmethod
    def _create_user(cls, name, *groups):
        login = name.lower().replace(" ", "_")
        return cls.env["res.users"].create(
            {
                "name": name,
                "login": f"sbl_{login}",
                "group_ids": [Command.set([group.id for group in groups])],
            },
        )

    def _add_stock(self, location, quantity, product=None):
        return self.Quant.sudo()._update_available_quantity(
            product or self.product, location, quantity
        )

    def _on_hand(self, location, product=None):
        quants = self.Quant.sudo().search(
            [
                ("product_id", "=", (product or self.product).id),
                ("location_id", "=", location.id),
            ],
        )
        return sum(quants.mapped("quantity"))

    def _create_delivery(self, user, location, quantity=10.0, product=None):
        product = product or self.product
        picking = self.Picking.with_user(user).create(
            {
                "location_id": location.id,
                "location_dest_id": self.customer_location.id,
                "picking_type_id": self.picking_type_out.id,
            },
        )
        self.Move.with_user(user).create(
            {
                "reference": f"SBL {location.name}",
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom_id": product.uom_id.id,
                "picking_id": picking.id,
                "location_id": location.id,
                "location_dest_id": self.customer_location.id,
            },
        )
        picking.action_confirm()
        return picking

    def _update_quantities_and_validate(self, picking, user):
        for line in picking.move_line_ids:
            line.quantity = line.quantity_product_uom
        picking.move_ids.picked = True
        return picking.with_user(user).button_validate()

    def _messages(self, record, needle):
        return record.message_ids.filtered(lambda m: needle in (m.body or ""))
