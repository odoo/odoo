from odoo.tests.common import tagged
from odoo.tests import Form, common

from datetime import datetime, timedelta
from contextlib import contextmanager


class TestProductMarginMRP(common.TransactionCase):

    @tagged("post_install", "-at_install")
    def test_product_margin_mrp(self):
        @contextmanager
        def rollback():
            savepoint = self.cr.savepoint()
            yield
            savepoint.rollback()

        product_to_build = self.env["product.product"].create({
            "name": "Main Product",
            "type": "product",
            "tracking": "none",
        })

        product_to_use_1 = self.env["product.product"].create({
            "name": "component_1",
            "type": "product",
            "tracking": "none",
            "standard_price": 10,
        })

        product_to_use_2 = self.env["product.product"].create({
            "name": "component_2",
            "type": "product",
            "tracking": "none",
            "standard_price": 20,
        })

        by_product_1 = self.env["product.product"].create({
            "name": "byproduct_1",
            "type": "product",
            "tracking": "none",
        })

        employee = self.env["hr.employee"].create({
            "name": "Demo Employee",
            "hourly_cost": 100,
        })
        uom_unit = self.env.ref("uom.product_uom_unit")
        workcenter_1 = self.env["mrp.workcenter"].create({
            "name": "Nuclear Workcenter",
            "default_capacity": 2,
            "time_start": 10,
            "time_stop": 5,
            "time_efficiency": 80,
            "employee_ids": [(4, employee.id)],
            "costs_hour": 50.0,
        })

        bom_1 = self.env["mrp.bom"].create({
            "product_id": product_to_build.id,
            "product_tmpl_id": product_to_build.product_tmpl_id.id,
            "product_uom_id": uom_unit.id,
            "product_qty": 1.0,
            "type": "normal",
            "consumption": "flexible",
            "bom_line_ids": [
                (0, 0, {"product_id": product_to_use_1.id, "product_qty": 4}),
                (0, 0, {"product_id": product_to_use_2.id, "product_qty": 4}),
            ],
            "byproduct_ids": [
                (0, 0, {
                        "product_id": by_product_1.id,
                        "product_qty": 1,
                        "cost_share": 5,
                })
            ],
            "operation_ids": [
                (0, 0, {
                        "name": "Demo work order",
                        "workcenter_id": workcenter_1.id,
                        "time_cycle": 15,
                        "sequence": 1,
                })
            ],
        })
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom_1
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.workorder_ids[0].button_start()
        mo.workorder_ids[0].button_finish()
        self.env["mrp.workcenter.productivity"].create({
                "employee_id": employee.id,
                "employee_cost": employee.hourly_cost,
                "workcenter_id": workcenter_1.id,
                "date_start": datetime.now() - timedelta(minutes=15),
                "date_end": datetime.now(),
                "description": self.env.ref("mrp.block_reason7").name,
                "loss_id": self.env.ref("mrp.block_reason7").id,
                "workorder_id": mo.workorder_ids[0].id,
        })
        mo.button_mark_done()
        self.assertEqual(mo.state, "done", "MO is not completed")
        mo.button_mark_done()
        with rollback():
            results = product_to_build._compute_product_margin_fields_values()
        components_cost = (10 * 4) + (20 * 4)
        workcenter_cost = 0.25 * 50
        employee_cost = 0.25 * 100
        operations_cost = workcenter_cost + employee_cost
        total_mo_cost = components_cost + operations_cost
        byproduct_cost = 0.05 * total_mo_cost
        total_manufacturing_cost_product = total_mo_cost - byproduct_cost
        method_output_nos_manufactured = results[product_to_build.id]["manufactured_num_products"]
        method_output_total_cost = results[product_to_build.id]["total_cost"]
        self.assertEqual(method_output_nos_manufactured, 1, "Incorrect number of manufactured products.")
        self.assertEqual(round(method_output_total_cost, 0), round(total_manufacturing_cost_product, 0), "Incorrect total manufacturing cost.")
