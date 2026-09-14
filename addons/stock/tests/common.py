import re

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product.tests.common import ProductVariantsCommon

RECEPTION_ROUTE_BOUGHT = "purchase_stock replaces the reception pull rule by a buy rule"


def is_module_installed(env, name):
    return env["ir.module.module"]._get(name).state == "installed"


class TestStockCommon(ProductVariantsCommon):
    def _create_move(self, product, src_location, dst_location, **values):
        Move = self.env["stock.move"].with_user(self.user_stock_manager)
        move = Move.new(
            {
                "product_id": product.id,
                "location_id": src_location.id,
                "location_dest_id": dst_location.id,
            }
        )
        move_values = move._convert_to_write(move._cache)
        move_values.update(**values)
        return Move.create(move_values)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.uom_dunit = cls.env["uom.uom"].create(
            {
                "name": "DeciUnit",
                "relative_factor": 10.0,
                "relative_uom_id": cls.uom_unit.id,
            }
        )

        cls.product_1, cls.product_2, cls.product_3 = cls.env["product.product"].create(
            [
                {
                    "name": "Courage",
                    "type": "consu",
                    "default_code": "PROD-1",
                    "uom_id": cls.uom_dunit.id,
                },
                {
                    "name": "Wood",
                },
                {
                    "name": "Stone",
                    "uom_id": cls.uom_dozen.id,
                },
            ]
        )

        cls.ProductObj = cls.env["product.product"]
        cls.UomObj = cls.env["uom.uom"]
        cls.PartnerObj = cls.env["res.partner"]
        cls.ModelDataObj = cls.env["ir.model.data"]
        cls.StockPackObj = cls.env["stock.move.line"]
        cls.StockQuantObj = cls.env["stock.quant"]
        cls.PickingObj = cls.env["stock.picking"]
        cls.MoveObj = cls.env["stock.move"]
        cls.LotObj = cls.env["stock.lot"]
        cls.StockLocationObj = cls.env["stock.location"]

        cls.warehouse_1 = cls.env["stock.warehouse"].create(
            {
                "name": "Base Warehouse",
                "reception_steps": "one_step",
                "delivery_steps": "ship_only",
                "code": "BWH",
                "sequence": 5,
            }
        )
        cls.route_mto = cls.warehouse_1.mto_pull_id.route_id
        cls.route_mto.rule_ids.procure_method = "make_to_order"

        cls.picking_type_in = cls.warehouse_1.in_type_id
        cls.picking_type_int = cls.warehouse_1.int_type_id
        cls.picking_type_out = cls.warehouse_1.out_type_id
        cls.picking_type_out.reservation_method = "manual"

        cls.stock_location = cls.warehouse_1.lot_stock_id
        cls.scrap_location = cls.StockLocationObj.search(
            [
                ("company_id", "=", cls.warehouse_1.company_id.id),
                ("usage", "=", "inventory"),
            ],
            limit=1,
        )
        cls.shelf_1, cls.shelf_2 = cls.StockLocationObj.create(
            [
                {
                    "name": "Shelf 1",
                    "location_id": cls.stock_location.id,
                },
                {
                    "name": "Shelf 2",
                    "location_id": cls.stock_location.id,
                },
            ]
        )

        pack_location = cls.warehouse_1.wh_pack_stock_loc_id
        pack_location.active = True
        cls.pack_location = pack_location
        output_location = cls.warehouse_1.wh_output_stock_loc_id
        output_location.active = True
        cls.output_location = output_location

        cls.supplier_location = cls.quick_ref("stock.stock_location_suppliers")
        cls.customer_location = cls.quick_ref("stock.stock_location_customers")
        cls.inter_company_location = cls.quick_ref("stock.stock_location_inter_company")

        (
            cls.productA,
            cls.productB,
            cls.productC,
            cls.productD,
            cls.productE,
        ) = cls.ProductObj.create(
            [
                {"name": "Product A", "is_storable": True},
                {"name": "Product B", "is_storable": True},
                {"name": "Product C", "is_storable": True},
                {"name": "Product D", "is_storable": True},
                {"name": "Product E", "is_storable": True},
            ]
        )

        cls.uom_kg = cls.uom_kgm
        cls.uom_gm = cls.uom_gram

        cls.kgB, cls.gB = cls.ProductObj.create(
            [
                {"name": "kg-B", "is_storable": True, "uom_id": cls.uom_kg.id},
                {"name": "g-B", "is_storable": True, "uom_id": cls.uom_gm.id},
            ]
        )

        cls.group_user.write(
            {
                "implied_ids": [
                    (4, cls.quick_ref("base.group_multi_company").id),
                    (4, cls.quick_ref("stock.group_production_lot").id),
                ]
            }
        )

        cls.user_stock_user = mail_new_test_user(
            cls.env,
            name="Pauline Poivraisselle",
            login="pauline",
            email="p.p@example.com",
            notification_type="inbox",
            groups="stock.group_stock_user",
        )
        cls.user_stock_manager = mail_new_test_user(
            cls.env,
            name="Julie Tablier",
            login="julie",
            email="j.j@example.com",
            notification_type="inbox",
            groups="stock.group_stock_manager",
        )

        cls.partner_1 = cls.env["res.partner"].create(
            {
                "name": "Julia Agrolait",
                "email": "julia@agrolait.example.com",
            }
        )

        cls.existing_inventories = cls.StockQuantObj.search(
            [("inventory_quantity", "!=", 0.0)]
        )
        cls.existing_quants = cls.StockQuantObj.search([])

    def url_extract_rec_id_and_model(self, url):
        action_match = re.findall(r"action-([^/]+)", url)
        model_name = self.env.ref(action_match[0]).res_model
        rec_id = re.findall(r"/(\d+)$", url)[0]
        return rec_id, model_name
