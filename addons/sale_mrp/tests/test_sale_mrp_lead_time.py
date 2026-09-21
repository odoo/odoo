from datetime import timedelta

from odoo import fields
from odoo.tests import Form

from odoo.addons.stock.tests.common import TestStockCommon


class TestSaleMrpLeadTime(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.route_mto.active = True
        with Form(cls.product_1) as p1:
            p1.is_storable = True
            p1.sale_delay = 5.0
            p1.route_ids.clear()
            p1.route_ids.add(cls.warehouse_1.manufacture_pull_id.route_id)
            p1.route_ids.add(cls.warehouse_1.mto_pull_id.route_id)

        with Form(cls.product_2) as p2:
            p2.type = "consu"

        with Form(cls.env["mrp.bom"]) as bom:
            bom.product_tmpl_id = cls.product_1.product_tmpl_id
            bom.product_qty = 2
            bom.produce_delay = 5.0
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.product_2
                line.product_qty = 4

        cls.warehouse_3_steps_pull = cls.env["stock.warehouse"].create(
            {
                "name": "Warehouse 3 steps",
                "code": "3S",
                "delivery_steps": "pick_pack_ship",
            }
        )
        delivery_route_3 = cls.warehouse_3_steps_pull.delivery_route_id
        delivery_route_3.rule_ids[0].write(
            {
                "location_dest_id": delivery_route_3.rule_ids[1].location_src_id.id,
            }
        )
        delivery_route_3.rule_ids[1].write({"action": "pull"})
        delivery_route_3.rule_ids[2].write({"action": "pull"})
        cls.warehouse_3_steps_pull.mto_pull_id.write(
            {
                "location_dest_id": delivery_route_3.rule_ids[1].location_src_id.id,
            }
        )

    def test_00_product_company_level_delays(self):
        company = self.env.ref("base.main_company")

        company.sale_config_id.security_lead = 3

        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner_1
        with order_form.line_ids.new() as line:
            line.product_id = self.product_1
            line.product_qty = 10
        order = order_form.save()
        order.action_confirm()

        manufacturing_order = self.env["mrp.production"].search(
            [
                ("product_id", "=", self.product_1.id),
                ("move_dest_ids", "in", order.picking_ids[0].move_ids.ids),
            ]
        )
        self.assertTrue(manufacturing_order, "Manufacturing order should be created.")

        deadline_picking = fields.Datetime.from_string(order.date_order) + timedelta(
            days=self.product_1.sale_delay
        )
        out_date = deadline_picking - timedelta(
            days=company.sale_config_id.security_lead
        )
        self.assertAlmostEqual(
            order.picking_ids[0].date_planned,
            out_date,
            delta=timedelta(seconds=1),
            msg="Schedule date of picking should be equal to: Order date + Customer Lead Time - Sales Safety Days.",
        )
        self.assertAlmostEqual(
            order.picking_ids[0].date_deadline,
            deadline_picking,
            delta=timedelta(seconds=1),
            msg="Deadline date of picking should be equal to: Order date + Customer Lead Time.",
        )

        mo_date_start = out_date - timedelta(
            days=manufacturing_order.bom_id.produce_delay
        )
        self.assertAlmostEqual(
            fields.Datetime.from_string(manufacturing_order.date_start),
            mo_date_start,
            delta=timedelta(seconds=1),
            msg="Schedule date of manufacturing order should be equal to: Schedule date of picking - product's Manufacturing Lead Time - company's Manufacturing Lead Time.",
        )
        self.assertAlmostEqual(
            fields.Datetime.from_string(manufacturing_order.date_deadline),
            deadline_picking,
            delta=timedelta(seconds=1),
            msg="Deadline date of manufacturing order should be equal to the deadline of sale picking",
        )

    def test_01_product_route_mrp_delays(self):
        warehouse = self.warehouse_3_steps_pull

        for pull_rule in warehouse.delivery_route_id.rule_ids:
            pull_rule.write({"delay": 2})

        order_form = Form(self.env["sale.order"])
        order_form.partner_id = self.partner_1
        order_form.warehouse_id = warehouse
        with order_form.line_ids.new() as line:
            line.product_id = self.product_1
            line.product_qty = 6
        order = order_form.save()
        order.action_confirm()

        self.env["stock.scheduler"].run()

        manufacturing_order = self.env["mrp.production"].search(
            [("product_id", "=", self.product_1.id)]
        )
        self.assertTrue(manufacturing_order, "Manufacturing order should be created.")

        self.assertTrue(order.picking_ids, "Pickings should be created.")

        out = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.out_type_id
        )
        out_min_date = fields.Datetime.from_string(out.date_planned)
        out_date = (
            fields.Datetime.from_string(order.date_order)
            + timedelta(days=self.product_1.sale_delay)
            - timedelta(days=out.move_ids[0].rule_id.delay)
        )
        self.assertAlmostEqual(
            out_min_date,
            out_date,
            delta=timedelta(seconds=10),
            msg="Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.",
        )

        pack = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.pack_type_id
        )
        pack_min_date = fields.Datetime.from_string(pack.date_planned)
        pack_date = out_date - timedelta(days=pack.move_ids[0].rule_id.delay)
        self.assertAlmostEqual(
            pack_min_date,
            pack_date,
            delta=timedelta(seconds=10),
            msg="Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.",
        )

        pick = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.pick_type_id
        )
        pick_min_date = fields.Datetime.from_string(pick.date_planned)
        self.assertAlmostEqual(
            pick_min_date,
            pack_date,
            delta=timedelta(seconds=10),
            msg="Schedule date of pick type picking should be equal to: Schedule date of pack type picking.",
        )

        mo_date_start = (
            out_date
            - timedelta(days=manufacturing_order.bom_id.produce_delay)
            - timedelta(days=warehouse.delivery_route_id.rule_ids[0].delay)
        )
        self.assertAlmostEqual(
            fields.Datetime.from_string(manufacturing_order.date_start),
            mo_date_start,
            delta=timedelta(seconds=1),
            msg="Schedule date of manufacturing order should be equal to: Schedule date of picking - product's Manufacturing Lead Time- delay pull_rule.",
        )
        self.assertAlmostEqual(
            manufacturing_order.date_deadline,
            order.picking_ids[0].date_deadline,
            delta=timedelta(seconds=1),
            msg="Deadline date of manufacturing order should be equal to the deadline of sale picking",
        )
