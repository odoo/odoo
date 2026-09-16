import re
from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import Form, tagged

from .common import TestMrpCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestMrpAuditFixes(TestMrpCommon):
    def test_report_bom_structure_merges_duplicate_component_qty(self):
        final = self.env["product.product"].create(
            {"name": "Audit Final", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Audit Component", "is_storable": True, "standard_price": 1.0}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": final.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 2.0}),
                    Command.create({"product_id": component.id, "product_qty": 3.0}),
                ],
            }
        )

        report = self.env["report.mrp.report_bom_structure"]
        data = report._get_report_data(bom_id=bom.id, searchQty=1, searchVariant=False)

        merged = [
            line
            for line in data["lines"]["components"]
            if line["product"].id == component.id
        ]
        self.assertEqual(
            len(merged), 1, "The duplicated component must be merged into one row."
        )
        self.assertAlmostEqual(
            merged[0]["base_bom_line_qty"],
            5.0,
            msg="Merged base_bom_line_qty must sum the two lines (2 + 3 = 5).",
        )
        self.assertAlmostEqual(merged[0]["quantity"], 5.0)

    def test_create_mo_with_non_create_finished_command_and_byproduct(self):
        final = self.env["product.product"].create(
            {"name": "Audit Final 2", "is_storable": True}
        )
        byproduct = self.env["product.product"].create(
            {"name": "Audit Byproduct", "is_storable": True}
        )
        picking_type = self.env["mrp.production"]._get_default_picking_type_id(
            self.env.company.id
        )

        mo = self.env["mrp.production"].create(
            {
                "product_id": final.id,
                "product_qty": 1.0,
                "picking_type_id": picking_type,
                "move_finished_ids": [Command.set([])],
                "move_byproduct_ids": [
                    Command.create(
                        {
                            "product_id": byproduct.id,
                            "product_uom_qty": 1.0,
                            "product_uom_id": byproduct.uom_id.id,
                            "location_id": self.env.ref(
                                "stock.stock_location_stock"
                            ).id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_stock"
                            ).id,
                        }
                    )
                ],
            }
        )
        self.assertIn(
            byproduct,
            mo.move_byproduct_ids.product_id,
            "The by-product move must survive the create() command normalization.",
        )

    def test_monetary_opt_widget_blanks_unset_amount(self):
        converter = self.env["ir.qweb.field.monetary_opt"]
        options = {"display_currency": self.env.company.currency_id}
        self.assertEqual(converter.value_to_html(False, options), "")
        self.assertEqual(converter.value_to_html(None, options), "")
        self.assertIn("oe_currency_value", converter.value_to_html(0.0, options))
        self.assertIn("oe_currency_value", converter.value_to_html(12.5, options))

    def test_mo_overview_report_renders_with_unset_costs(self):
        self.workcenter_1.costs_hour = 0.0
        product = (
            self.bom_2.product_id or self.bom_2.product_tmpl_id.product_variant_ids[:1]
        )
        mo = self.env["mrp.production"].create(
            {"product_id": product.id, "bom_id": self.bom_2.id, "product_qty": 1.0}
        )
        mo.action_confirm()
        html, content_type = self.env["ir.actions.report"]._render_qweb_html(
            "mrp.report_mo_overview",
            mo.ids,
            data={
                "moCosts": "1",
                "bomCosts": "1",
                "realCosts": "1",
                "unfoldedIds": "[]",
            },
        )
        self.assertEqual(content_type, "html")
        self.assertTrue(html, "The MO Overview report should render non-empty HTML.")

    def test_bom_producible_qty_sums_mixed_uom_component_lines(self):
        unit = self.env.ref("uom.product_uom_unit")
        dozen = self.env.ref("uom.product_uom_dozen")
        component = self.env["product.product"].create(
            {"name": "Mixed-UoM Component", "is_storable": True, "uom_id": unit.id}
        )
        finished = self.env["product.product"].create(
            {"name": "Mixed-UoM Finished", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component.id,
                            "product_qty": 2.0,
                            "product_uom_id": unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": component.id,
                            "product_qty": 1.0,
                            "product_uom_id": dozen.id,
                        }
                    ),
                ],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            component, self.env.ref("stock.stock_location_stock"), 28.0
        )
        data = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom.id, searchQty=1, searchVariant=False
        )
        comp_rows = [
            line
            for line in data["lines"]["components"]
            if line["product"].id == component.id
        ]
        self.assertEqual(
            len(comp_rows), 2, "Different-UoM component lines must not be merged."
        )
        self.assertEqual(
            data["lines"]["producible_qty"],
            2.0,
            "Ready-To-Produce must sum mixed-UoM demand (2u + 1doz = 14u) against "
            "28u of stock -> 2.",
        )

    def test_bom_create_syncs_product_uom_id(self):
        square_meter = self.env.ref("uom.product_uom_square_meter")
        template = self.env["product.template"].create(
            {"name": "Audit m2 product", "uom_id": square_meter.id}
        )
        bom = self.env["mrp.bom"].create(
            {"product_tmpl_id": template.id, "product_qty": 1.0}
        )
        self.assertEqual(
            bom.product_uom_id,
            square_meter,
            "BoM UoM must follow the product's UoM when not given explicitly.",
        )

    def test_routing_bom_change_removes_only_moved_operation_blocker(self):
        product = self.env["product.product"].create(
            {"name": "Audit Dep Final", "is_storable": True}
        )
        wc = self.workcenter_1
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_qty": 1.0,
                "allow_operation_dependencies": True,
                "operation_ids": [
                    Command.create({"name": "OP A", "workcenter_id": wc.id}),
                    Command.create({"name": "OP B", "workcenter_id": wc.id}),
                    Command.create({"name": "OP C", "workcenter_id": wc.id}),
                ],
            }
        )
        op_a, op_b, op_c = bom.operation_ids
        op_c.blocked_by_operation_ids = [Command.set((op_a + op_b).ids)]
        self.assertEqual(op_c.blocked_by_operation_ids, op_a + op_b)

        other_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_qty": 1.0,
                "allow_operation_dependencies": True,
            }
        )
        op_a.bom_id = other_bom.id
        self.assertEqual(
            op_c.blocked_by_operation_ids,
            op_b,
            "Only the moved operation (A) may be removed; B must remain a blocker.",
        )

    def test_explode_detects_phantom_cycle(self):
        prod_a = self.env["product.product"].create(
            {"name": "Cycle A", "is_storable": True}
        )
        prod_b = self.env["product.product"].create(
            {"name": "Cycle B", "is_storable": True}
        )
        bom_a = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": prod_a.product_tmpl_id.id,
                "product_id": prod_a.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )
        bom_b = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": prod_b.product_tmpl_id.id,
                "product_id": prod_b.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )
        self.env.cr.execute(
            """
            INSERT INTO mrp_bom_line (product_id, product_uom_id, bom_id, product_qty)
            VALUES (%s, %s, %s, 1), (%s, %s, %s, 1)
            """,
            (
                prod_b.id,
                prod_b.uom_id.id,
                bom_a.id,
                prod_a.id,
                prod_a.uom_id.id,
                bom_b.id,
            ),
        )
        self.env["mrp.bom"].invalidate_model()
        self.env["mrp.bom.line"].invalidate_model()
        with self.assertRaises(ValidationError):
            bom_a._explode(prod_a, 1.0)

    def test_bom_rejects_product_uom_of_another_category(self):
        kgm = self.env.ref("uom.product_uom_kgm")
        unit = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "Audit uom-category product", "uom_id": unit.id}
        )
        with self.assertRaises(ValidationError):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": template.id,
                    "product_qty": 1.0,
                    "product_uom_id": kgm.id,
                }
            )

    def test_bom_accepts_convertible_product_uom(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        unit = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "Audit dozen product", "uom_id": unit.id}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": template.id,
                "product_qty": 1.0,
                "product_uom_id": dozen.id,
            }
        )
        self.assertEqual(bom.product_uom_id, dozen)

    def test_bom_line_rejects_product_uom_of_another_category(self):
        kgm = self.env.ref("uom.product_uom_kgm")
        unit = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "Audit line parent", "uom_id": unit.id}
        )
        component = self.env["product.product"].create(
            {"name": "Audit line component", "uom_id": unit.id}
        )
        with self.assertRaises(ValidationError):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": template.id,
                    "product_qty": 1.0,
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component.id,
                                "product_qty": 1.0,
                                "product_uom_id": kgm.id,
                            }
                        )
                    ],
                }
            )

    def test_byproduct_rejects_product_uom_of_another_category(self):
        kgm = self.env.ref("uom.product_uom_kgm")
        unit = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "Audit byproduct parent", "uom_id": unit.id}
        )
        byproduct = self.env["product.product"].create(
            {"name": "Audit byproduct", "uom_id": unit.id}
        )
        with self.assertRaises(ValidationError):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": template.id,
                    "product_qty": 1.0,
                    "byproduct_ids": [
                        Command.create(
                            {
                                "product_id": byproduct.id,
                                "product_qty": 1.0,
                                "product_uom_id": kgm.id,
                            }
                        )
                    ],
                }
            )

    def _audit_mo_with_two_workorders(self):
        unit = self.env.ref("uom.product_uom_unit")
        finished = self.env["product.product"].create(
            {"name": "Audit WO finished", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Audit WO component", "is_storable": True}
        )
        workcenter_a = self.env["mrp.workcenter"].create(
            {"name": "Audit WC A", "time_efficiency": 100.0}
        )
        workcenter_b = self.env["mrp.workcenter"].create(
            {"name": "Audit WC B", "time_efficiency": 100.0}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": unit.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 1.0, "bom_id": bom.id}
        )
        workorders = self.env["mrp.workorder"].create(
            [
                {
                    "name": "Audit WO 1",
                    "workcenter_id": workcenter_a.id,
                    "product_uom_id": unit.id,
                    "production_id": production.id,
                    "duration_expected": 60.0,
                },
                {
                    "name": "Audit WO 2",
                    "workcenter_id": workcenter_b.id,
                    "product_uom_id": unit.id,
                    "production_id": production.id,
                    "duration_expected": 30.0,
                },
            ]
        )
        return production, workorders

    def test_workorder_write_keeps_per_record_end_date(self):
        _production, workorders = self._audit_mo_with_two_workorders()
        start = datetime(2030, 1, 1, 8, 0, 0)
        workorders.write({"date_start": start, "date_end": start + timedelta(hours=1)})
        self.assertEqual(workorders[0].date_end, start + timedelta(minutes=60))
        self.assertEqual(workorders[1].date_end, start + timedelta(minutes=30))

    def test_workorder_write_keeps_per_record_duration(self):
        _production, workorders = self._audit_mo_with_two_workorders()
        base = datetime(2030, 2, 1, 6, 0, 0)
        workorders[0].write(
            {
                "date_start": base,
                "date_end": base + timedelta(hours=6),
                "duration_expected": 360.0,
            }
        )
        workorders[1].write(
            {
                "date_start": base,
                "date_end": base + timedelta(hours=10),
                "duration_expected": 600.0,
            }
        )
        workorders.write({"date_start": base + timedelta(hours=1)})
        self.assertNotEqual(
            workorders[0].duration_expected,
            workorders[1].duration_expected,
            "the two work orders span different intervals and cannot share a duration",
        )

    def test_workorder_write_does_not_mutate_caller_vals(self):
        _production, workorders = self._audit_mo_with_two_workorders()
        vals = {
            "date_start": datetime(2030, 3, 1, 8, 0, 0),
            "date_end": datetime(2030, 3, 1, 9, 0, 0),
        }
        snapshot = dict(vals)
        workorders[1].write(vals)
        self.assertEqual(vals, snapshot)

    def _audit_two_productions(self):
        unit = self.env.ref("uom.product_uom_unit")
        finished = self.env["product.product"].create(
            {"name": "Audit MO finished", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Audit MO component", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": unit.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        productions = self.env["mrp.production"].create(
            [
                {"product_id": finished.id, "product_qty": 5.0, "bom_id": bom.id},
                {"product_id": finished.id, "product_qty": 5.0, "bom_id": bom.id},
            ]
        )
        return productions, component, unit

    def test_production_write_multi_record_with_raw_moves(self):
        productions, component, unit = self._audit_two_productions()
        productions.action_confirm()
        productions.write(
            {
                "move_raw_ids": [
                    Command.create(
                        {
                            "product_id": component.id,
                            "product_uom_qty": 1.0,
                            "product_uom_id": unit.id,
                        }
                    )
                ]
            }
        )
        for production in productions:
            added = production.move_raw_ids.filtered(lambda m: not m.bom_line_id)
            self.assertEqual(len(added), 1)
            self.assertEqual(
                added.warehouse_id, production.location_src_id.warehouse_id
            )

    def test_production_write_multi_record_product_id_is_dropped(self):
        productions, _component, _unit = self._audit_two_productions()
        original = productions.product_id
        productions.action_confirm()
        other = self.env["product.product"].create(
            {"name": "Audit MO other", "is_storable": True}
        )
        productions.write({"product_id": other.id})
        self.assertEqual(productions.product_id, original)

    def test_production_write_does_not_mutate_caller_vals(self):
        productions, _component, _unit = self._audit_two_productions()
        productions.action_confirm()
        vals = {"product_id": productions[0].product_id.id, "priority": "1"}
        snapshot = dict(vals)
        productions.write(vals)
        self.assertEqual(vals, snapshot)

    def test_get_name_backorder_reads_its_own_group(self):
        self.assertEqual(
            self.env["mrp.production"]._get_name_backorder("WH/MO/00001-002", 3),
            "WH/MO/00001-003",
        )

    def test_autoprint_mass_generated_lots_without_label_format(self):
        productions, _component, _unit = self._audit_two_productions()
        picking_type = productions[0].picking_type_id
        picking_type.write(
            {
                "auto_print_generated_mrp_lot": True,
                "generated_mrp_lot_label_to_print": False,
            }
        )
        self.assertEqual(productions._prepare_actions_autoprint_generated_lots(), [])

    def test_bom_overview_attachment_lookup(self):
        report = self.env["report.mrp.report_bom_structure"]
        on_variant = self.env["product.product"].create(
            {"name": "Audit attach variant", "is_storable": True}
        )
        on_template = self.env["product.product"].create(
            {"name": "Audit attach template", "is_storable": True}
        )
        plain = self.env["product.product"].create(
            {"name": "Audit attach none", "is_storable": True}
        )
        self.env["document.document"].create(
            [
                {
                    "name": "variant-spec.txt",
                    "attached_on_mrp": "bom",
                    "res_model": "product.product",
                    "res_id": on_variant.id,
                },
                {
                    "name": "template-spec.txt",
                    "attached_on_mrp": "bom",
                    "res_model": "product.template",
                    "res_id": on_template.product_tmpl_id.id,
                },
            ]
        )
        self.assertTrue(report._has_bom_attachment(on_variant))
        self.assertFalse(
            report._has_bom_attachment(template=on_variant.product_tmpl_id)
        )
        self.assertTrue(report._has_bom_attachment(on_template))
        self.assertTrue(
            report._has_bom_attachment(template=on_template.product_tmpl_id)
        )
        self.assertFalse(report._has_bom_attachment(plain))
        self.assertFalse(report._has_bom_attachment(template=plain.product_tmpl_id))

    def test_bom_counts_are_deduplicated(self):
        unit = self.env.ref("uom.product_uom_unit")
        finished = self.env["product.product"].create(
            {"name": "Count finished", "is_storable": True}
        )
        other = self.env["product.product"].create(
            {"name": "Count other", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Count component", "is_storable": True}
        )

        def bom(product, lines, byproducts=()):
            return self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "product_uom_id": unit.id,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": c.id, "product_qty": qty})
                        for c, qty in lines
                    ],
                    "byproduct_ids": [
                        Command.create(
                            {
                                "product_id": p.id,
                                "product_qty": 1.0,
                                "product_uom_id": unit.id,
                            }
                        )
                        for p in byproducts
                    ],
                }
            )

        bom(finished, [(component, 1.0)])
        bom(finished, [(component, 2.0)])
        bom(other, [(component, 1.0), (component, 5.0)], byproducts=(finished,))
        self.env.invalidate_all()

        self.assertEqual(finished.product_tmpl_id.bom_count, 3)
        self.assertEqual(other.product_tmpl_id.bom_count, 1)
        self.assertEqual(component.product_tmpl_id.used_in_bom_count, 3)
        self.assertEqual(component.product_tmpl_id.bom_count, 0)

    def test_unbuild_without_bom_or_mo_is_refused(self):
        product = self.env["product.product"].create(
            {"name": "Unbuild no BoM", "is_storable": True}
        )
        unbuild = self.env["mrp.unbuild"].create(
            {
                "product_id": product.id,
                "product_qty": 1.0,
                "product_uom_id": product.uom_id.id,
            }
        )
        self.assertFalse(unbuild.bom_id)
        self.assertFalse(unbuild.mo_id)
        self.env["stock.quant"].create(
            {
                "location_id": unbuild.location_id.id,
                "product_id": product.id,
                "inventory_quantity": 10,
            }
        ).action_apply_inventory()
        with self.assertRaises(UserError):
            unbuild.action_validate()

    def test_show_allocation_without_warehouse_on_operation_type(self):
        self.env.user.group_ids = [
            Command.link(self.env.ref("mrp.group_mrp_reception_report").id)
        ]
        finished, component = self.env["product.product"].create(
            [
                {"name": "Alloc finished", "is_storable": True},
                {"name": "Alloc component", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        picking_type = warehouse.manu_type_id.copy(
            {"name": "Manufacturing (no warehouse)", "sequence_code": "MONOWH"}
        )
        picking_type.warehouse_id = False
        self.assertFalse(picking_type.warehouse_id)

        production = self.env["mrp.production"].create(
            {
                "product_id": finished.id,
                "bom_id": bom.id,
                "product_qty": 1.0,
                "picking_type_id": picking_type.id,
            }
        )
        self.env.flush_all()
        production.invalidate_recordset()
        self.assertFalse(
            production.web_read({"id": {}, "show_allocation": {}})[0]["show_allocation"]
        )

    def test_production_state_leaves_progress_when_nothing_is_consumed(self):
        production = self.generate_mo()[0]
        production.action_confirm()
        self.env.flush_all()
        self.assertEqual(production.state, "confirmed")

        production.move_raw_ids.picked = True
        self.env.flush_all()
        production.invalidate_recordset()
        self.assertEqual(production.state, "progress")

        production.move_raw_ids.picked = False
        production.qty_producing = 0
        self.env.flush_all()
        production.invalidate_recordset()
        self.assertEqual(production.state, "confirmed")

    def test_draft_production_is_not_confirmed_by_its_state_compute(self):
        production = self.env["mrp.production"].create(
            {"product_id": self.product_4.id, "product_qty": 1.0}
        )
        self.env.flush_all()
        self.assertEqual(production.state, "draft")

        production.invalidate_recordset()
        self.env.add_to_compute(production._fields["state"], production)
        self.env.flush_all()
        self.assertEqual(production.state, "draft")

    def test_picking_type_is_computed_per_company(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Audit second company"})
        self.env["stock.warehouse"].create(
            {"name": "Audit WH B", "code": "AWB", "company_id": company_b.id}
        )
        self.env.user.company_ids = [Command.link(company_b.id)]
        env = self.env(
            context=dict(
                self.env.context, allowed_company_ids=[company_a.id, company_b.id]
            )
        )
        product = env["product.product"].create({"name": "Two-company product"})

        productions = env["mrp.production"].create(
            [
                {
                    "name": "AUDIT/0001",
                    "product_id": product.id,
                    "product_qty": 1.0,
                    "company_id": company_a.id,
                },
                {
                    "name": "AUDIT/0002",
                    "product_id": product.id,
                    "product_qty": 1.0,
                    "company_id": company_b.id,
                },
            ]
        )
        env.flush_all()
        for production in productions:
            self.assertTrue(production.picking_type_id)
            self.assertEqual(
                production.picking_type_id.warehouse_id.company_id,
                production.company_id,
            )

    def test_deleting_a_workorder_keeps_its_predecessors_other_edges(self):
        production = self.env["mrp.production"].create(
            {"product_id": self.product_4.id, "product_qty": 1.0}
        )
        production.allow_workorder_dependencies = True
        workorder_a, workorder_b, workorder_c = self.env["mrp.workorder"].create(
            [
                {
                    "name": name,
                    "production_id": production.id,
                    "workcenter_id": self.workcenter_1.id,
                }
                for name in ("Manual A", "Manual B", "Manual C")
            ]
        )
        workorder_a.blocked_by_workorder_ids = [Command.set(workorder_b.ids)]
        workorder_c.blocked_by_workorder_ids = [Command.set(workorder_b.ids)]
        self.env.flush_all()
        self.assertEqual(workorder_b.needed_by_workorder_ids, workorder_a | workorder_c)

        workorder_a.unlink()
        self.env.flush_all()
        (workorder_b | workorder_c).invalidate_recordset()
        self.assertEqual(workorder_b.needed_by_workorder_ids, workorder_c)
        self.assertEqual(workorder_c.blocked_by_workorder_ids, workorder_b)

    def test_planned_workorders_may_be_rescheduled_onto_each_other(self):
        finished, component = self.env["product.product"].create(
            [
                {"name": "Replan finished", "is_storable": True},
                {"name": "Replan component", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Replan operation",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle_manual": 60,
                        }
                    )
                ],
            }
        )
        productions = self.env["mrp.production"].create(
            [
                {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
                for _ in range(2)
            ]
        )
        productions.button_plan()
        self.env.flush_all()
        first, second = productions[0].workorder_ids, productions[1].workorder_ids
        self.assertEqual(first.reservation_id.enforcement_mode, "soft")

        second.write({"date_start": first.date_start, "date_end": first.date_end})
        self.env.flush_all()
        self.assertEqual(second.date_start, first.date_start)
        self.assertIn(second.id, first._get_conflicted_workorder_ids()[first.id])

    def test_manual_consumption_flag_is_a_boolean(self):
        Move = self.env["stock.move"]
        self.assertIs(
            Move._is_manual_consumption_from_bom_line(self.env["mrp.bom.line"]), False
        )
        bom = self.bom_1
        bom.operation_ids = [
            Command.create({"name": "Flag op", "workcenter_id": self.workcenter_1.id})
        ]
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0]
        self.assertIs(
            Move._is_manual_consumption_from_bom_line(bom.bom_line_ids[0]), True
        )

    def test_variant_bom_counts_match_their_template_counterparts(self):
        finished, other, component = self.env["product.product"].create(
            [
                {"name": "Variant counts finished", "is_storable": True},
                {"name": "Variant counts other", "is_storable": True},
                {"name": "Variant counts component", "is_storable": True},
            ]
        )
        unit = self.env.ref("uom.product_uom_unit")
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": finished.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "bom_line_ids": [
                        Command.create({"product_id": component.id, "product_qty": 1.0})
                    ],
                },
                {
                    "product_tmpl_id": finished.product_tmpl_id.id,
                    "product_id": finished.id,
                    "product_qty": 2.0,
                },
                {
                    "product_tmpl_id": other.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "byproduct_ids": [
                        Command.create(
                            {
                                "product_id": finished.id,
                                "product_qty": 1.0,
                                "product_uom_id": unit.id,
                            }
                        )
                    ],
                    "bom_line_ids": [
                        Command.create(
                            {"product_id": component.id, "product_qty": 5.0}
                        ),
                        Command.create(
                            {"product_id": component.id, "product_qty": 7.0}
                        ),
                    ],
                },
            ]
        )
        self.env.invalidate_all()
        self.assertEqual(finished.bom_count, 3)
        self.assertEqual(finished.product_tmpl_id.bom_count, 3)
        self.assertEqual(component.used_in_bom_count, 2)
        self.assertEqual(component.product_tmpl_id.used_in_bom_count, 2)
        self.assertEqual(component.bom_count, 0)

    def _count_queries(self, callback, pattern):
        cursor = self.env.cr
        original = cursor.execute
        matched = []

        def spy(query, *args, **kwargs):
            if re.search(pattern, str(query), re.IGNORECASE):
                matched.append(query)
            return original(query, *args, **kwargs)

        cursor.execute = spy
        try:
            callback()
        finally:
            cursor.execute = original
        return len(matched)

    def test_orderpoint_bom_placeholder_does_not_scale_with_the_row_count(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        products = self.env["product.product"].create(
            [{"name": f"Placeholder {i}", "is_storable": True} for i in range(20)]
        )
        self.env["mrp.bom"].create(
            [
                {"product_tmpl_id": product.product_tmpl_id.id, "product_qty": 1.0}
                for product in products
            ]
        )
        orderpoints = self.env["stock.warehouse.orderpoint"].create(
            [
                {
                    "product_id": product.id,
                    "warehouse_id": warehouse.id,
                    "location_id": warehouse.lot_stock_id.id,
                    "product_min_qty": 1.0,
                    "product_max_qty": 5.0,
                }
                for product in products
            ]
        )
        self.env.flush_all()

        def read_placeholders():
            orderpoints.invalidate_recordset(["bom_id_placeholder"])
            orderpoints.mapped("bom_id_placeholder")

        queries = self._count_queries(read_placeholders, r"\bmrp_bom\b")
        self.assertLessEqual(
            queries,
            4,
            "resolving the default BoM of %s orderpoints took %s mrp_bom queries;"
            " it must not scale with the number of rows" % (len(orderpoints), queries),
        )

    def test_variant_bom_counters_do_not_scale_with_the_record_count(self):
        products = self.env["product.product"].create(
            [{"name": f"Counter {i}", "is_storable": True} for i in range(20)]
        )
        self.env["mrp.bom"].create(
            [
                {"product_tmpl_id": product.product_tmpl_id.id, "product_qty": 1.0}
                for product in products
            ]
        )
        self.env.flush_all()

        for field in ("bom_count", "used_in_bom_count"):

            def read_field(field=field):
                products.invalidate_recordset([field])
                products.mapped(field)

            queries = self._count_queries(read_field, r"\bmrp_bom")
            self.assertLessEqual(
                queries,
                3,
                "%s took %s mrp_bom queries for %s products"
                % (field, queries, len(products)),
            )

    def test_live_duration_reports_a_running_timer(self):
        production = self.generate_mo()[0]
        workorder = self.env["mrp.workorder"].create(
            {
                "name": "Live duration",
                "production_id": production.id,
                "workcenter_id": self.workcenter_1.id,
            }
        )
        loss = self.env["mrp.workcenter.productivity.loss"].search(
            [("loss_type", "=", "productive")], limit=1
        )
        self.env["mrp.workcenter.productivity"].create(
            {
                "workorder_id": workorder.id,
                "workcenter_id": self.workcenter_1.id,
                "loss_id": loss.id,
                "date_start": fields.Datetime.now() - timedelta(minutes=30),
            }
        )
        self.env.flush_all()
        workorder.invalidate_recordset()

        self.assertAlmostEqual(workorder.duration_live, 30.0, delta=1.0)
        self.assertAlmostEqual(
            workorder.duration_live, workorder.get_duration(), delta=1.0
        )
        self.assertEqual(workorder.time_ids.duration, 0.0)
        self.assertEqual(
            workorder.duration,
            0.0,
            "a timer that is still running counts for nothing in the stored "
            "duration, which is what makes it a function of the timer rows",
        )

    def test_live_duration_matches_the_stored_one_when_nothing_runs(self):
        production = self.generate_mo()[0]
        workorder = self.env["mrp.workorder"].create(
            {
                "name": "Closed timer",
                "production_id": production.id,
                "workcenter_id": self.workcenter_1.id,
            }
        )
        loss = self.env["mrp.workcenter.productivity.loss"].search(
            [("loss_type", "=", "productive")], limit=1
        )
        ended = self.env.cr.now()
        self.env["mrp.workcenter.productivity"].create(
            {
                "workorder_id": workorder.id,
                "workcenter_id": self.workcenter_1.id,
                "loss_id": loss.id,
                "date_start": ended - timedelta(minutes=12),
                "date_end": ended,
            }
        )
        self.env.flush_all()
        workorder.invalidate_recordset()

        self.assertAlmostEqual(workorder.duration, 12.0, delta=0.1)
        self.assertAlmostEqual(workorder.duration_live, workorder.duration)

    def test_creating_orders_costs_no_query_per_order_for_its_moves(self):
        """`all_move_raw_ids` and `all_move_ids` are read by nothing and load-bearing.

        They are the undomained siblings of `move_raw_ids` and
        `move_finished_ids`. `modified()` navigates from a written `stock.move`
        back to the productions whose dependent fields need recomputing, and it
        does that through an inverse One2many — which the domained pair cannot
        serve. Deleting them as dead (no reference in odoo, enterprise,
        agromarin or design-themes, and none in any stored expression) cost two
        queries per order created, and no test said so.

        The threshold also guards the batching in `_create_deferred_moves`: a
        `Command.create` inside the x2many assignment is flushed by that
        assignment, so a compute that assigns per record calls
        `stock.move.create()` per record. Deferring the vals took the marginal
        cost from 4.0 to 1.27, and 2.0 is below both the 4.0 that per-record
        creates cost and the 6.0 that losing the undomained inverses cost.

        The guard is the marginal cost of one more order, not a total: a total
        moves with every unrelated change and a budget only fails above itself.
        """
        component = self.env["product.product"].create(
            {"name": "Marginal component", "is_storable": True}
        )
        product = self.env["product.product"].create(
            {"name": "Marginal", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 2})
                ],
            }
        )

        def cost(count):
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            self.env["mrp.production"].create(
                [
                    {"product_id": product.id, "product_qty": 1.0, "bom_id": bom.id}
                    for _ in range(count)
                ]
            )
            self.env.flush_all()
            return self.env.cr.sql_statement_count - before

        few, many = cost(2), cost(12)
        per_order = (many - few) / 10
        self.assertLess(
            per_order,
            2.0,
            "creating a manufacturing order must not cost a query per order for "
            "its own moves: %s queries for 2 orders, %s for 12, %.2f per order"
            % (few, many, per_order),
        )

    def test_a_timer_that_starts_after_the_transaction_did_still_accrues(self):
        """The bound on a running timer must be the clock that stamped its start.

        It was `cr.now()`, PostgreSQL's transaction timestamp, so a timer whose
        `date_start` fell after the transaction began spanned backwards and
        `Intervals` dropped it -- a work order started five seconds into its own
        transaction reported a live duration of exactly zero. Freezing the
        wall clock ahead of the transaction reproduces that ordering exactly,
        without depending on how long this test's transaction has been open.
        """
        with freeze_time("2099-03-01 10:00:00"):
            workorder = self._audit_workorder_with_timer(
                "Ahead of the cursor", started_minutes_ago=60
            )
            self.assertGreater(
                workorder.time_ids.date_start,
                self.env.cr.now(),
                "the timer must open after the transaction did for this to bite",
            )
            self.assertEqual(workorder.duration_live, 60.0)

    def test_a_frozen_clock_freezes_the_live_duration(self):
        """A live duration read twice under a frozen clock reads the same twice.

        It did not: the running timer was bounded by `cr.now()`, which is
        PostgreSQL's clock and which `freeze_time` cannot reach. Under a freeze
        that put `date_start` in 2020, the unfrozen bound made the interval
        years wide -- the same defect that made a real 5-second-old transaction
        report zero, seen from the other side.
        """
        with freeze_time("2020-05-04 10:00:00"):
            workorder = self._audit_workorder_with_timer(
                "Frozen", started_minutes_ago=45
            )
            self.assertEqual(workorder.time_ids.date_start, datetime(2020, 5, 4, 9, 15))
            self.assertEqual(workorder.duration_live, 45.0)
            self.assertEqual(workorder.duration_live, workorder.get_duration())
            self.assertEqual(workorder.duration, 0.0)

    def test_the_stored_duration_agrees_with_the_sum_of_its_timer_rows(self):
        """One figure, two routes: the ORM field and the SQL the reports run.

        `mrp_account_enterprise` reads `SUM(mrp_workcenter_productivity.duration)`
        and `mrp_workorder_hr_account` reads `SUM(mrp_workorder.duration)`. They
        are the same quantity and disagreed by the live accrual of every running
        timer.
        """
        workorder = self._audit_workorder_with_timer(
            "Two numbers", started_minutes_ago=30
        )
        self.env.cr.execute(
            "SELECT COALESCE(SUM(duration), 0) FROM mrp_workcenter_productivity"
            " WHERE workorder_id = %s",
            (workorder.id,),
        )
        [[summed_rows]] = self.env.cr.fetchall()
        self.env.cr.execute(
            "SELECT duration FROM mrp_workorder WHERE id = %s", (workorder.id,)
        )
        [[stored]] = self.env.cr.fetchall()
        self.assertEqual(stored, summed_rows)
        self.assertAlmostEqual(workorder.duration_live, 30.0, delta=1.0)

    def _audit_workorder_with_timer(self, name, started_minutes_ago):
        production = self.generate_mo()[0]
        workorder = self.env["mrp.workorder"].create(
            {
                "name": name,
                "production_id": production.id,
                "workcenter_id": self.workcenter_1.id,
            }
        )
        loss = self.env["mrp.workcenter.productivity.loss"].search(
            [("loss_type", "=", "productive")], limit=1
        )
        self.env["mrp.workcenter.productivity"].create(
            {
                "workorder_id": workorder.id,
                "workcenter_id": self.workcenter_1.id,
                "loss_id": loss.id,
                "date_start": fields.Datetime.now()
                - timedelta(minutes=started_minutes_ago),
            }
        )
        self.env.flush_all()
        workorder.invalidate_recordset()
        return workorder

    def test_live_duration_is_computed_for_the_whole_list_at_once(self):
        production = self.generate_mo()[0]
        workorders = self.env["mrp.workorder"].create(
            [
                {
                    "name": f"Batch live {index}",
                    "production_id": production.id,
                    "workcenter_id": self.workcenter_1.id,
                }
                for index in range(5)
            ]
        )
        self.env.flush_all()
        workorders.invalidate_recordset()
        self.assertEqual(workorders.mapped("duration_live"), [0.0] * 5)

    def test_mo_overview_rounds_costs_in_the_orders_own_currency(self):
        jpy = (
            self.env["res.currency"]
            .with_context(active_test=False)
            .search([("name", "=", "JPY")], limit=1)
        )
        jpy.active = True
        self.assertLess(
            jpy.decimal_places,
            self.env.company.currency_id.decimal_places,
            "this test needs a viewing currency coarser than the order's",
        )
        viewer_company = self.env["res.company"].create(
            {"name": "Coarse currency viewer", "currency_id": jpy.id}
        )
        self.env["stock.warehouse"].create(
            {"name": "CCV", "code": "CCV", "company_id": viewer_company.id}
        )
        self.env.user.company_ids = [Command.link(viewer_company.id)]

        finished, component = self.env["product.product"].create(
            [
                {"name": "Currency finished", "is_storable": True},
                {"name": "Currency component", "is_storable": True},
            ]
        )
        workcenter = self.env["mrp.workcenter"].create(
            {"name": "Currency workcenter", "costs_hour": 37.0}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Currency operation",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 17,
                        }
                    )
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
        )
        production.action_confirm()
        production.workorder_ids.unlink()
        self.env.flush_all()

        report = self.env["report.mrp.report_mo_overview"].with_company(viewer_company)
        self.assertEqual(report.env.company, viewer_company)
        bom_cost = report._get_report_data(production.id)["summary"]["bom_cost"]

        order_currency = production.company_id.currency_id
        self.assertAlmostEqual(bom_cost, order_currency.round(10.4833), places=2)
        self.assertNotAlmostEqual(bom_cost, 10.0, places=2)

    def test_split_wizard_bounds_the_batch_count_on_the_onchange_path(self):
        product = self.env["product.product"].create(
            {"name": "Split bound", "is_storable": True}
        )
        production = self.env["mrp.production"].create(
            {"product_id": product.id, "product_qty": 100000.0}
        )
        wizard = self.env["mrp.production.split"].create(
            {"production_id": production.id}
        )
        max_splits = wizard.MAX_SPLITS
        self.assertEqual(len(wizard.production_detailed_vals_ids), 1)

        with self.assertRaises(ValidationError), Form(wizard) as form:
            form.max_batch_size = 20.0
        self.assertEqual(len(wizard.production_detailed_vals_ids), 1)

        with Form(wizard) as form:
            form.max_batch_size = production.product_qty / max_splits
            self.assertEqual(form.num_splits, max_splits)
        self.assertEqual(len(wizard.production_detailed_vals_ids), max_splits)

    def test_delay_alert_search_answers_what_the_field_shows(self):
        component = self.env["product.product"].create(
            {"name": "Delay alert component", "is_storable": True},
        )
        finished = self.env["product.product"].create(
            {"name": "Delay alert finished", "is_storable": True},
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1,
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1}),
                ],
            },
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 1, "bom_id": bom.id},
        )
        production.action_confirm()
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        upstream = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.int_type_id.id,
                "move_ids": [
                    Command.create(
                        {"product_id": component.id, "product_uom_qty": 1},
                    ),
                ],
            },
        )
        upstream.action_confirm()
        production.move_raw_ids.move_orig_ids = [Command.set(upstream.move_ids.ids)]
        upstream.move_ids.date = datetime(2031, 12, 1)
        production.move_raw_ids.date = datetime(2030, 1, 1)
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(production.date_delay_alert, datetime(2031, 12, 1))
        Production = self.env["mrp.production"]
        for operator, value, expected in (
            ("!=", False, True),
            (">", datetime(2031, 6, 1), True),
            ("<", datetime(2031, 6, 1), False),
            ("=", datetime(2031, 12, 1), True),
            ("=", datetime(2031, 1, 1), False),
        ):
            with self.subTest(operator=operator, value=value):
                self.assertEqual(
                    bool(
                        Production.search(
                            [
                                ("id", "=", production.id),
                                ("date_delay_alert", operator, value),
                            ],
                        )
                    ),
                    expected,
                    "the search must classify by the same rule the field shows",
                )

        self.assertTrue(
            Production.search(
                [
                    ("id", "=", production.id),
                    "|",
                    ("date_delay_alert", "!=", False),
                    ("is_delayed", "=", True),
                ],
            ),
            "the Late filter the search view ships must find a delayed order",
        )

    def _kit_with_one_component(self, on_hand):
        component = self.env["product.product"].create(
            {"name": "Audit Kit Component", "is_storable": True}
        )
        kit = self.env["product.product"].create(
            {"name": "Audit Kit", "is_storable": True}
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1})
                ],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            component, self.stock_location, on_hand
        )
        return kit, component

    def test_kit_quantities_are_readable_without_manufacturing_rights(self):
        kit, __ = self._kit_with_one_component(7.0)
        reader = mail_new_test_user(
            self.env,
            login="audit_kit_reader",
            name="Audit Kit Reader",
            groups="stock.group_stock_user",
        )
        self.assertFalse(
            reader.has_group("mrp.group_mrp_user"),
            "the reader must not carry manufacturing rights for this to measure "
            "anything",
        )

        self.assertEqual(
            kit.with_user(reader).qty_available,
            7.0,
            "a reader without manufacturing rights must get the kit's quantity, "
            "not an AccessError on mrp.bom",
        )

    def test_kit_component_quantities_still_obey_the_reader_record_rules(self):
        kit, component = self._kit_with_one_component(7.0)
        reader = mail_new_test_user(
            self.env,
            login="audit_kit_ruled_reader",
            name="Audit Kit Ruled Reader",
            groups="stock.group_stock_user",
        )
        self.env["ir.rule"].create(
            {
                "name": "Audit: no quant is visible",
                "model_id": self.env["ir.model"]._get_id("stock.quant"),
                "domain_force": "[(0, '=', 1)]",
                "groups": [Command.link(self.quick_ref("stock.group_stock_user").id)],
            }
        )

        self.assertEqual(
            component.with_user(reader).qty_available,
            0.0,
            "the rule must hide the component's own quantity, or this test "
            "cannot tell the two environments apart",
        )
        self.assertEqual(
            kit.with_user(reader).qty_available,
            0.0,
            "the kit's quantity is its components': elevating the BoM lookup "
            "must not elevate the components' quant reads",
        )

    def _audit_cancel_fixture(self, consumption="flexible", with_byproduct=False):
        unit = self.env.ref("uom.product_uom_unit")
        finished = self.env["product.product"].create(
            {"name": "Audit cancel finished", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Audit cancel component", "is_storable": True}
        )
        byproduct = self.env["product.product"].create(
            {"name": "Audit cancel byproduct", "is_storable": True}
        )
        bom_vals = {
            "product_tmpl_id": finished.product_tmpl_id.id,
            "product_qty": 1.0,
            "product_uom_id": unit.id,
            "type": "normal",
            "consumption": consumption,
            "bom_line_ids": [
                Command.create({"product_id": component.id, "product_qty": 1.0})
            ],
        }
        if with_byproduct:
            bom_vals["byproduct_ids"] = [
                Command.create(
                    {
                        "product_id": byproduct.id,
                        "product_qty": 1.0,
                        "product_uom_id": unit.id,
                    }
                )
            ]
        bom = self.env["mrp.bom"].create(bom_vals)
        location = self.env["stock.warehouse"].search([], limit=1).lot_stock_id
        self.env["stock.quant"]._update_available_quantity(component, location, 100)
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 2.0, "bom_id": bom.id}
        )
        production.action_confirm()
        production.action_assign()
        production.qty_producing = 1
        production._update_moves_from_qty_producing()
        return production

    def test_cancelling_a_part_consumed_order_lands_on_cancel(self):
        production = self._audit_cancel_fixture()
        production.move_raw_ids.picked = True
        production.move_raw_ids._action_done()
        self.assertEqual(production.state, "progress")

        production.action_cancel()
        production.invalidate_recordset()
        self.assertEqual(
            production.state,
            "cancel",
            "every finished move is cancelled, so _compute_state decides cancel; "
            "_action_cancel used to write 'done' here and the write never ran",
        )

    def test_cancelling_leaves_a_produced_byproduct_order_done(self):
        production = self._audit_cancel_fixture(with_byproduct=True)
        byproduct_move = production.move_byproduct_ids
        byproduct_move.quantity = 1
        byproduct_move.picked = True
        byproduct_move._action_done()
        production.move_raw_ids.picked = True
        production.move_raw_ids._action_done()

        production.action_cancel()
        production.invalidate_recordset()
        self.assertEqual(
            production.state,
            "done",
            "not every finished move is cancelled, so _compute_state reaches its "
            "own done branch on its own -- this is the outcome the deleted block "
            "claimed to produce",
        )

    def test_cancelling_does_not_depend_on_the_boms_consumption(self):
        states = {}
        for consumption in ("flexible", "strict"):
            production = self._audit_cancel_fixture(consumption=consumption)
            production.move_raw_ids.picked = True
            production.move_raw_ids._action_done()
            production.action_cancel()
            production.invalidate_recordset()
            states[consumption] = production.state
        self.assertEqual(
            states["flexible"],
            states["strict"],
            "the deleted block only fired for flexible BoMs; if consumption ever "
            "changes the cancel outcome, it is a new rule and needs its own home",
        )

    def _audit_one_production(self):
        unit = self.env.ref("uom.product_uom_unit")
        finished = self.env["product.product"].create(
            {"name": "Audit depends finished", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Audit depends component", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": unit.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 3.0, "bom_id": bom.id}
        )
        production.action_confirm()
        return production, component, unit

    def test_scrap_count_follows_its_own_scraps(self):
        production, component, unit = self._audit_one_production()
        self.assertEqual(production.scrap_count, 0)

        self.env["stock.scrap"].create(
            {
                "production_id": production.id,
                "product_id": component.id,
                "product_uom_id": unit.id,
                "scrap_qty": 1,
            }
        )

        self.assertEqual(len(production.scrap_ids), 1)
        self.assertEqual(
            production.scrap_count,
            1,
            "the compute declared no dependency at all, so the count stayed at "
            "its first reading for the whole transaction",
        )

    def test_transfer_count_follows_the_groups_moves(self):
        production, component, unit = self._audit_one_production()
        self.assertEqual(production.count_transfer_outgoing, 0)

        picking_type = self.env["stock.picking.type"].search(
            [("code", "in", ("internal", "outgoing"))], limit=1
        )
        self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": production.location_src_id.id,
                "location_dest_id": production.location_dest_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": component.id,
                            "product_uom_qty": 1,
                            "product_uom_id": unit.id,
                            "location_id": production.location_src_id.id,
                            "location_dest_id": production.location_dest_id.id,
                            "production_group_id": production.production_group_id.id,
                        }
                    )
                ],
            }
        )

        self.assertEqual(
            production.count_transfer_outgoing,
            1,
            "the compute depended on `state`, which no part of it reads, so a "
            "picking appearing in the group never invalidated it",
        )

    def test_availability_follows_its_moves_without_borrowing_reservation_state(self):
        production, _component, _unit = self._audit_one_production()
        self.assertEqual(production.components_availability_state, "unavailable")

        production.move_raw_ids.product_uom_qty = 0
        self.assertEqual(
            production.components_availability_state,
            "available",
            "the body reads move.state and move.product_qty; it used to reach "
            "them only through reservation_state's own dependency list",
        )

    def _audit_availability_population(self):
        unit = self.env.ref("uom.product_uom_unit")
        location = self.env["stock.warehouse"].search([], limit=1).lot_stock_id
        start = datetime(2026, 9, 15, 8, 0, 0)
        made = {}
        for tag, stocked, incoming_days in (
            ("avail", True, None),
            ("short", False, None),
            ("late", False, 20),
            ("soon", False, -5),
        ):
            component = self.env["product.product"].create(
                {"name": "Audit avail %s c" % tag, "is_storable": True}
            )
            finished = self.env["product.product"].create(
                {"name": "Audit avail %s f" % tag, "is_storable": True}
            )
            if stocked:
                self.env["stock.quant"]._update_available_quantity(
                    component, location, 100
                )
            bom = self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": finished.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "product_uom_id": unit.id,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": component.id, "product_qty": 1.0})
                    ],
                }
            )
            production = self.env["mrp.production"].create(
                {
                    "product_id": finished.id,
                    "product_qty": 2.0,
                    "bom_id": bom.id,
                    "date_start": start,
                }
            )
            production.action_confirm()
            if stocked:
                production.action_assign()
            if incoming_days is not None:
                incoming = self.env["stock.picking.type"].search(
                    [("code", "=", "incoming")], limit=1
                )
                self.env["stock.move"].create(
                    {
                        "product_id": component.id,
                        "product_uom_qty": 100,
                        "product_uom_id": unit.id,
                        "location_id": self.env.ref(
                            "stock.stock_location_suppliers"
                        ).id,
                        "location_dest_id": location.id,
                        "picking_type_id": incoming.id,
                        "date": start + timedelta(days=incoming_days),
                    }
                )._action_confirm()
            made[tag] = production
        return made

    def _availability_state_by_scan(self, value):
        open_orders = self.env["mrp.production"].search(
            [("state", "in", ("confirmed", "progress", "to_close"))]
        )
        return set(
            open_orders.filtered(lambda p: p.components_availability_state in value).ids
        )

    def test_availability_search_matches_a_full_scan_for_every_state(self):
        made = self._audit_availability_population()
        self.assertEqual(
            {tag: p.components_availability_state for tag, p in made.items()},
            {
                "avail": "available",
                "short": "unavailable",
                "late": "late",
                "soon": "expected",
            },
            "the fixture must cover all four states or the comparison is vacuous",
        )

        production = self.env["mrp.production"]
        for value in (
            ["available"],
            ["unavailable"],
            ["late"],
            ["expected"],
            ["available", "late"],
            ["unavailable", "expected"],
            ["available", "unavailable", "late", "expected"],
        ):
            self.assertEqual(
                set(
                    production.search(
                        [("components_availability_state", "in", value)]
                    ).ids
                ),
                self._availability_state_by_scan(value),
                "the SQL pre-filter changed the answer for %s" % value,
            )

    def test_availability_search_skips_the_fully_reserved_orders(self):
        made = self._audit_availability_population()
        production = self.env["mrp.production"]
        candidates = production.search(
            production._get_domain_components_availability_open()
            & Domain(
                "move_raw_ids",
                "any",
                production._get_domain_components_availability_unsettled_move(),
            )
        )
        self.assertNotIn(
            made["avail"],
            candidates,
            "a fully reserved order can produce neither a shortage nor a forecast "
            "date, so it must never reach the Python compute",
        )
        for tag in ("short", "late", "soon"):
            self.assertIn(made[tag], candidates)

    def _audit_byproduct_fixture(self):
        unit = self.env.ref("uom.product_uom_unit")
        finished = self.env["product.product"].create(
            {"name": "Audit byp finished", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Audit byp component", "is_storable": True}
        )
        byproduct = self.env["product.product"].create(
            {"name": "Audit byp byproduct", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": unit.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        return finished, byproduct, bom, unit

    def test_creating_with_the_byproduct_key_alone_keeps_the_finished_product(self):
        finished, byproduct, bom, unit = self._audit_byproduct_fixture()
        bom.byproduct_ids = [
            Command.create({"product_id": byproduct.id, "product_qty": 2.0})
        ]
        moves_before = self.env["stock.move"].search(
            [("product_id", "in", (finished | byproduct).ids)]
        )

        production = self.env["mrp.production"].create(
            {
                "product_id": finished.id,
                "product_qty": 1.0,
                "bom_id": bom.id,
                "move_byproduct_ids": [
                    Command.create(
                        {
                            "product_id": byproduct.id,
                            "product_uom_qty": 2,
                            "product_uom_id": unit.id,
                        }
                    )
                ],
            }
        )

        self.assertEqual(
            sorted(production.move_finished_ids.product_id.mapped("name")),
            sorted([finished.name, byproduct.name]),
            "the product's own finished move must exist beside the by-product's",
        )
        moves_after = (
            self.env["stock.move"].search(
                [("product_id", "in", (finished | byproduct).ids)]
            )
            - moves_before
        )
        self.assertEqual(
            moves_after,
            production.move_finished_ids,
            "no finished move may be left outside the order (an orphan by-product "
            "move from the compute that the inverse then detached)",
        )

    def test_writing_both_move_keys_keeps_the_byproduct(self):
        finished, byproduct, bom, unit = self._audit_byproduct_fixture()
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 1.0, "bom_id": bom.id}
        )

        production.write(
            {
                "move_finished_ids": [
                    Command.update(
                        production.move_finished_ids[0].id, {"product_uom_qty": 2}
                    )
                ],
                "move_byproduct_ids": [
                    Command.create(
                        {
                            "product_id": byproduct.id,
                            "product_uom_qty": 1,
                            "product_uom_id": unit.id,
                        }
                    )
                ],
            }
        )

        self.assertIn(
            byproduct,
            production.move_finished_ids.product_id,
            "the merge used to be gated on bom_id also being in vals; without it "
            "the byproduct command was dropped and no stock.move was ever created",
        )
        self.assertTrue(
            self.env["stock.move"].search_count(
                [
                    ("product_id", "=", byproduct.id),
                    ("production_id", "=", production.id),
                ]
            )
        )

    def test_writing_both_move_keys_matches_creating_with_both(self):
        finished, byproduct, bom, unit = self._audit_byproduct_fixture()

        def byproduct_command():
            return Command.create(
                {
                    "product_id": byproduct.id,
                    "product_uom_qty": 1,
                    "product_uom_id": unit.id,
                }
            )

        created = self.env["mrp.production"].create(
            {
                "product_id": finished.id,
                "product_qty": 1.0,
                "bom_id": bom.id,
                "move_finished_ids": [
                    Command.create(
                        {
                            "product_id": finished.id,
                            "product_uom_qty": 1,
                            "product_uom_id": unit.id,
                        }
                    )
                ],
                "move_byproduct_ids": [byproduct_command()],
            }
        )
        written = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 1.0, "bom_id": bom.id}
        )
        written.write({"move_byproduct_ids": [byproduct_command()]})

        self.assertEqual(
            sorted(created.move_finished_ids.product_id.mapped("name")),
            sorted(written.move_finished_ids.product_id.mapped("name")),
            "create() and write() must fold the byproduct key the same way",
        )

    def test_writing_product_id_on_a_mixed_set_still_reaches_the_draft_orders(self):
        productions, _component, _unit = self._audit_two_productions()
        draft, confirmed = productions[0], productions[1]
        confirmed.action_confirm()
        original = confirmed.product_id
        other = self.env["product.product"].create(
            {"name": "Audit mixed other", "is_storable": True}
        )

        productions.write({"product_id": other.id})

        self.assertEqual(
            draft.product_id,
            other,
            "a draft order used to lose its product change because a confirmed "
            "sibling was in the same recordset",
        )
        self.assertEqual(confirmed.product_id, original)

    def test_every_path_agrees_on_the_orders_production_location(self):
        unit = self.env.ref("uom.product_uom_unit")
        company = self.env.company
        finished_location = self.env["stock.location"].create(
            {"name": "Audit prod FIN", "usage": "production", "company_id": company.id}
        )
        component_location = self.env["stock.location"].create(
            {"name": "Audit prod COMP", "usage": "production", "company_id": company.id}
        )
        finished = self.env["product.product"].create(
            {"name": "Audit prodloc finished", "is_storable": True}
        )
        component = self.env["product.product"].create(
            {"name": "Audit prodloc component", "is_storable": True}
        )
        finished.with_company(company).property_stock_production = finished_location
        component.with_company(company).property_stock_production = component_location
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": unit.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 2.0, "bom_id": bom.id}
        )
        expected = production.production_location_id
        self.assertEqual(expected, finished_location)

        raw_move = production.move_raw_ids
        self.assertEqual(raw_move.location_dest_id, expected)
        self.assertEqual(production.move_finished_ids.location_id, expected)
        self.assertEqual(
            production._prepare_move_raw_vals(
                component, 1.0, unit, bom_line=bom.bom_line_ids[0]
            )["location_dest_id"],
            expected.id,
            "the vals builder used to spell this as the finished product's own "
            "property_stock_production, with no company fallback",
        )

        linked = self.env["stock.move"].create(
            {
                "product_id": component.id,
                "product_uom_qty": 1,
                "product_uom_id": unit.id,
                "location_id": production.location_src_id.id,
                "location_dest_id": production.location_src_id.id,
                "company_id": company.id,
            }
        )
        linked.write({"raw_material_production_id": production.id})
        self.assertEqual(
            linked.location_dest_id,
            expected,
            "the compute used to answer with the component's production location, "
            "which disagreed with everything that actually got saved",
        )

    def _audit_confirmed_orders(self, count, tag):
        unit = self.env.ref("uom.product_uom_unit")
        location = self.env["stock.warehouse"].search([], limit=1).lot_stock_id
        components = self.env["product.product"].create(
            [
                {"name": "Audit batch %s c%d" % (tag, i), "is_storable": True}
                for i in range(count)
            ]
        )
        finished = self.env["product.product"].create(
            [
                {"name": "Audit batch %s f%d" % (tag, i), "is_storable": True}
                for i in range(count)
            ]
        )
        for component in components:
            self.env["stock.quant"]._update_available_quantity(
                component, location, 1000
            )
        boms = self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "product_uom_id": unit.id,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": component.id, "product_qty": 1.0})
                    ],
                }
                for component, product in zip(components, finished, strict=True)
            ]
        )
        productions = self.env["mrp.production"].create(
            [
                {"product_id": product.id, "product_qty": 1.0, "bom_id": bom.id}
                for product, bom in zip(finished, boms, strict=True)
            ]
        )
        productions.action_confirm()
        self.env.flush_all()
        return productions, unit

    def _write_an_extra_component_cost(self, count, tag):
        productions, unit = self._audit_confirmed_orders(count, tag)
        extra = self.env["product.product"].create(
            {"name": "Audit batch %s extra" % tag, "is_storable": True}
        )
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        productions.write(
            {
                "move_raw_ids": [
                    Command.create(
                        {
                            "product_id": extra.id,
                            "product_uom_qty": 1.0,
                            "product_uom_id": unit.id,
                        }
                    )
                ]
            }
        )
        self.env.flush_all()
        queries = self.env.cr.sql_statement_count - before
        added = productions.move_raw_ids.filtered(lambda m: not m.bom_line_id)
        self.assertEqual(len(added), count, "one move per order, whatever the batching")
        return queries

    def test_writing_moves_to_many_orders_costs_one_batch(self):
        small = self._write_an_extra_component_cost(2, "small")
        large = self._write_an_extra_component_cost(20, "large")
        marginal = (large - small) / 18.0
        self.assertLess(
            marginal,
            10,
            "write() used to recurse once per record whenever a move key was in "
            "vals, so each extra order cost a full write of its own (~18 queries). "
            "N=2 cost %d, N=20 cost %d, marginal %.1f" % (small, large, marginal),
        )

    def test_writing_moves_still_splits_across_warehouses(self):
        productions, unit = self._audit_confirmed_orders(2, "wh")
        other_warehouse = self.env["stock.warehouse"].create(
            {"name": "Audit second WH", "code": "AWH2"}
        )
        productions[1].location_src_id = other_warehouse.lot_stock_id
        extra = self.env["product.product"].create(
            {"name": "Audit wh extra", "is_storable": True}
        )
        productions.write(
            {
                "move_raw_ids": [
                    Command.create(
                        {
                            "product_id": extra.id,
                            "product_uom_qty": 1.0,
                            "product_uom_id": unit.id,
                        }
                    )
                ]
            }
        )
        for production in productions:
            added = production.move_raw_ids.filtered(lambda m: not m.bom_line_id)
            self.assertEqual(
                added.warehouse_id,
                production.location_src_id.warehouse_id,
                "the batch may only group orders that share a source warehouse",
            )

    def _audit_serial_byproduct_order(self, line_count, tag):
        unit = self.env.ref("uom.product_uom_unit")
        location = self.env["stock.warehouse"].search([], limit=1).lot_stock_id
        component = self.env["product.product"].create(
            {"name": "Audit sn %s c" % tag, "is_storable": True}
        )
        finished = self.env["product.product"].create(
            {"name": "Audit sn %s f" % tag, "is_storable": True}
        )
        byproduct = self.env["product.product"].create(
            {"name": "Audit sn %s b" % tag, "is_storable": True, "tracking": "serial"}
        )
        self.env["stock.quant"]._update_available_quantity(component, location, 1000)
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": unit.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": byproduct.id,
                            "product_qty": 1.0,
                            "product_uom_id": unit.id,
                        }
                    )
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {
                "product_id": finished.id,
                "product_qty": line_count,
                "bom_id": bom.id,
            }
        )
        production.action_confirm()
        production.qty_producing = line_count
        production._update_moves_from_qty_producing()
        byproduct_move = production.move_byproduct_ids
        byproduct_move.move_line_ids.unlink()
        lots = self.env["stock.lot"].create(
            [
                {"name": "AUDITSN-%s-%d" % (tag, i), "product_id": byproduct.id}
                for i in range(line_count)
            ]
        )
        self.env["stock.move.line"].create(
            [
                {
                    "move_id": byproduct_move.id,
                    "product_id": byproduct.id,
                    "quantity": 1,
                    "lot_id": lot.id,
                    "product_uom_id": unit.id,
                    "location_id": byproduct_move.location_id.id,
                    "location_dest_id": byproduct_move.location_dest_id.id,
                }
                for lot in lots
            ]
        )
        self.env.flush_all()
        return production

    def _sn_uniqueness_cost(self, line_count, tag):
        production = self._audit_serial_byproduct_order(line_count, tag)
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        production._check_sn_uniqueness()
        return self.env.cr.sql_statement_count - before

    def test_checking_serial_byproducts_costs_one_batch(self):
        small = self._sn_uniqueness_cost(2, "small")
        large = self._sn_uniqueness_cost(20, "large")
        marginal = (large - small) / 18.0
        self.assertLess(
            marginal,
            0.5,
            "_is_any_finished_serial_already_produced was called once per serial "
            "byproduct line and opened with a search_count every time. N=2 cost "
            "%d, N=20 cost %d, marginal %.2f" % (small, large, marginal),
        )

    def test_marking_a_batch_done_stamps_one_end_date(self):
        productions, _unit = self._audit_confirmed_orders(6, "markdone")
        for production in productions:
            production.qty_producing = production.product_qty
            production._update_moves_from_qty_producing()
        self.env.flush_all()

        productions.with_context(
            skip_backorder=True, skip_consumption=True
        ).button_mark_done()
        productions.invalidate_recordset()

        self.assertEqual(
            set(productions.mapped("state")),
            {"done"},
        )
        self.assertEqual(
            len(set(productions.mapped("date_end"))),
            1,
            "one click closes one batch, so it ends at one instant; the loop used "
            "to call fields.Datetime.now() once per order",
        )

    def test_byproduct_finished_moves_carry_no_destinations(self):
        finished, byproduct, bom, unit = self._audit_byproduct_fixture()
        bom.write(
            {
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": byproduct.id,
                            "product_qty": 1.0,
                            "product_uom_id": unit.id,
                        }
                    )
                ]
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 1.0, "bom_id": bom.id}
        )

        byproduct_move = production.move_byproduct_ids
        self.assertTrue(byproduct_move, "the fixture must produce a byproduct move")
        self.assertFalse(
            byproduct_move.move_dest_ids,
            "only the order's own finished product carries the destinations; "
            "resolving them walks references -> orders -> groups -> orders, and "
            "a byproduct used to pay for that walk and then discard it",
        )
        self.assertEqual(
            production._prepare_move_finished_vals(
                byproduct.id, 1.0, unit.id, byproduct_id=bom.byproduct_ids[0].id
            )["move_dest_ids"],
            [],
        )

    def test_reservation_state_follows_the_bom_it_asks_about(self):
        first, second, finished = self.env["product.product"].create(
            [
                {"name": "Ready First", "is_storable": True},
                {"name": "Ready Second", "is_storable": True},
                {"name": "Ready Finished", "is_storable": True},
            ]
        )
        workcenter = self.env["mrp.workcenter"].create({"name": "Ready WC"})
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "ready_to_produce": "all_available",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "first",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 10,
                        }
                    ),
                    Command.create(
                        {
                            "name": "second",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 10,
                        }
                    ),
                ],
            }
        )
        operations = bom.operation_ids
        bom.bom_line_ids = [
            Command.create(
                {
                    "product_id": first.id,
                    "product_qty": 1.0,
                    "operation_id": operations[0].id,
                }
            ),
            Command.create(
                {
                    "product_id": second.id,
                    "product_qty": 1.0,
                    "operation_id": operations[1].id,
                }
            ),
        ]
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 10.0}
        )
        production.action_confirm()
        warehouse = production.picking_type_id.warehouse_id
        self.env["stock.quant"]._update_available_quantity(
            first, warehouse.lot_stock_id, 100.0
        )
        production.action_assign()
        self.assertEqual(
            production.move_raw_ids.mapped("state"),
            ["assigned", "confirmed"],
            "the fixture needs the first operation reserved and the second not",
        )
        self.assertEqual(production.reservation_state, "confirmed")

        bom.ready_to_produce = "asap"
        self.env.flush_all()
        production.invalidate_recordset(["reservation_state"])
        self.assertEqual(
            production.reservation_state,
            "assigned",
            "a stored field must not keep an answer its own input has changed",
        )

    def test_one_bom_is_exploded_once_for_a_whole_batch_of_orders(self):
        kit_component, leaf, finished = self.env["product.product"].create(
            [
                {"name": "Batch Kit", "is_storable": True},
                {"name": "Batch Leaf", "is_storable": True},
                {"name": "Batch Finished", "is_storable": True},
            ]
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit_component.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create({"product_id": leaf.id, "product_qty": 1.0})
                ],
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": kit_component.id, "product_qty": 1.0})
                ],
            }
        )

        MrpBom = type(self.env["mrp.bom"])
        unpatched = MrpBom._get_bom_by_product

        def explosions_for(count):
            calls = []

            def counting(bom_self, *args, **kwargs):
                calls.append(None)
                return unpatched(bom_self, *args, **kwargs)

            self.env.flush_all()
            self.patch(MrpBom, "_get_bom_by_product", counting)
            self.env["mrp.production"].create(
                [
                    {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
                    for _ in range(count)
                ]
            )
            self.env.flush_all()
            return len(calls)

        few = explosions_for(2)
        many = explosions_for(20)
        self.assertLessEqual(
            many - few,
            few,
            "resolving the kit closure must not scale with the number of orders: "
            f"{few} lookups for 2 orders, {many} for 20",
        )

    def test_show_lot_ids_follows_its_components_tracking(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Lot Column Component", "is_storable": True},
                {"name": "Lot Column Finished", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
        )
        production.action_confirm()
        self.assertFalse(production.show_lot_ids)

        component.tracking = "serial"
        self.env.flush_all()
        self.assertTrue(
            production.show_lot_ids,
            "the column has to appear as soon as a component is tracked",
        )

    def test_splitting_two_orders_of_one_group_numbers_them_apart(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Split Seq Component", "is_storable": True},
                {"name": "Split Seq Finished", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 10.0}
        )
        production.action_confirm()
        siblings = production._split_productions({production: [4.0, 6.0]})
        self.assertEqual(len(siblings), 2)
        self.assertEqual(
            siblings.production_group_id,
            production.production_group_id,
            "the fixture needs both orders in one group",
        )

        split = siblings._split_productions(
            {order: [1.0, order.product_qty - 1.0] for order in siblings}
        )

        self.assertEqual(len(split), 4)
        self.assertEqual(
            sorted(split.mapped("backorder_sequence")),
            [1, 2, 3, 4],
            "every order in a group carries its own sequence",
        )
        self.assertEqual(
            len(set(split.mapped("name"))),
            4,
            "and therefore its own name",
        )

    def test_the_kit_closure_memo_is_keyed_on_the_company_that_resolved_it(self):
        other = self.env["res.company"].create({"name": "Kit Memo Co"})
        kit, first, second, finished = self.env["product.product"].create(
            [
                {"name": "Memo Kit", "is_storable": True},
                {"name": "Memo First", "is_storable": True},
                {"name": "Memo Second", "is_storable": True},
                {"name": "Memo Finished", "is_storable": True},
            ]
        )
        for company, leaf in ((self.env.company, first), (other, second)):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": kit.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "type": "phantom",
                    "company_id": company.id,
                    "bom_line_ids": [
                        Command.create({"product_id": leaf.id, "product_qty": 1.0})
                    ],
                }
            )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "company_id": False,
                "bom_line_ids": [
                    Command.create({"product_id": kit.id, "product_qty": 1.0})
                ],
            }
        )

        scratch = self.env["mrp.bom"]._get_explosion_scratch()
        resolved = {}
        for company, expected in ((self.env.company, first), (other, second)):
            _boms, lines = bom.with_context(
                bom_cost_share_cache=scratch,
                company_id=company.id,
                allowed_company_ids=[company.id],
            )._explode(finished, 1.0)
            resolved[company] = lines[0][0].product_id
            self.assertEqual(
                resolved[company],
                expected,
                f"{company.display_name} must get its own kit, not a memoised one",
            )
        self.assertNotEqual(*resolved.values())

    def test_the_unbuild_bom_lookup_is_the_same_answer_in_a_batch(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "Unbuild Batch Size",
                "create_variant": "always",
                "value_ids": [
                    Command.create({"name": "S"}),
                    Command.create({"name": "L"}),
                ],
            }
        )
        leaf = self.env["product.product"].create(
            {"name": "Unbuild Leaf", "is_storable": True}
        )
        products = self.env["product.product"]
        for index, (variant_sequence, template_sequence) in enumerate(
            ((9, 1), (1, 9), (5, 5))
        ):
            template = self.env["product.template"].create(
                {
                    "name": f"Unbuild Batch {index}",
                    "is_storable": True,
                    "attribute_line_ids": [
                        Command.create(
                            {
                                "attribute_id": attribute.id,
                                "value_ids": [Command.set(attribute.value_ids.ids)],
                            }
                        )
                    ],
                }
            )
            self.env["mrp.bom"].create(
                [
                    {
                        "product_tmpl_id": template.id,
                        "product_qty": 1.0,
                        "type": "normal",
                        "sequence": template_sequence,
                        "bom_line_ids": [
                            Command.create({"product_id": leaf.id, "product_qty": 1.0})
                        ],
                    },
                    {
                        "product_tmpl_id": template.id,
                        "product_id": template.product_variant_ids[0].id,
                        "product_qty": 1.0,
                        "type": "normal",
                        "sequence": variant_sequence,
                        "bom_line_ids": [
                            Command.create({"product_id": leaf.id, "product_qty": 2.0})
                        ],
                    },
                ]
            )
            products |= template.product_variant_ids
        products |= self.env["product.product"].create(
            {"name": "Unbuild No Bom", "is_storable": True}
        )
        self.env.flush_all()

        orders = self.env["mrp.unbuild"].create(
            [{"product_id": product.id, "product_qty": 1.0} for product in products]
        )
        one_at_a_time = []
        for order in orders:
            order.invalidate_recordset(["bom_id"])
            one_at_a_time.append(order.bom_id)
        orders.invalidate_recordset(["bom_id"])
        orders.mapped("bom_id")

        self.assertEqual(
            [order.bom_id for order in orders],
            one_at_a_time,
            "the grouped lookup must answer what the per-record one did",
        )
        self.assertTrue(any(one_at_a_time), "the fixture must resolve at least one BoM")

    def test_production_capacity_counts_the_components_that_have_stock(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Capacity Component", "is_storable": True},
                {"name": "Capacity Finished", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 2.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1000.0}
        )
        warehouse = production.picking_type_id.warehouse_id
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 14.0
        )
        self.env.flush_all()

        self.assertEqual(
            production.move_raw_ids.product_id,
            component,
            "the fixture must put a storable component on a raw move",
        )
        self.assertEqual(
            production.production_capacity,
            7.0,
            "14 components at 2 per unit is 7 units, not the 1000 asked for",
        )

        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 6.0
        )
        production.invalidate_recordset(["production_capacity"])
        self.assertEqual(production.production_capacity, 10.0)

    def test_changing_the_quantity_closes_a_work_order_that_is_already_done(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Reopen Component", "is_storable": True},
                {"name": "Reopen Finished", "is_storable": True},
            ]
        )
        workcenter = self.env["mrp.workcenter"].create({"name": "Reopen WC"})
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "op",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 10,
                        }
                    )
                ],
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 10.0}
        )
        production.action_confirm()
        workorder = production.workorder_ids
        workorder.qty_produced = 10.0
        workorder.state = "progress"
        self.env.flush_all()

        self.env["change.production.qty"].create(
            {"mo_id": production.id, "product_qty": 5.0}
        ).change_prod_qty()

        self.assertTrue(
            workorder.is_produced,
            "the fixture must leave the work order over its new target",
        )
        self.assertEqual(
            workorder.state,
            "done",
            "a work order with nothing left to make must not sit at 'progress'",
        )

    def test_changing_the_quantity_reopens_a_work_order_that_is_not_done(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Reopen2 Component", "is_storable": True},
                {"name": "Reopen2 Finished", "is_storable": True},
            ]
        )
        workcenter = self.env["mrp.workcenter"].create({"name": "Reopen2 WC"})
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "op",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 10,
                        }
                    )
                ],
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 5.0}
        )
        production.action_confirm()
        workorder = production.workorder_ids
        workorder.qty_produced = 5.0
        workorder.state = "done"
        self.env.flush_all()

        self.env["change.production.qty"].create(
            {"mo_id": production.id, "product_qty": 20.0}
        ).change_prod_qty()

        self.assertFalse(workorder.is_produced)
        self.assertEqual(workorder.state, "progress")

    def test_show_allocation_answers_the_same_thing_for_a_whole_list(self):
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        other_warehouse = self.env["stock.warehouse"].search(
            [("id", "!=", warehouse.id), ("company_id", "=", warehouse.company_id.id)],
            limit=1,
        ) or self.env["stock.warehouse"].create(
            {
                "name": "Allocation WH2",
                "code": "AL2",
                "company_id": warehouse.company_id.id,
            }
        )
        customers = self.env.ref("stock.stock_location_customers")
        self.env.user.group_ids = [
            Command.link(self.env.ref("mrp.group_mrp_reception_report").id)
        ]
        component = self.env["product.product"].create(
            {"name": "Allocation Component", "is_storable": True}
        )
        for house in (warehouse, other_warehouse):
            self.env["stock.quant"]._update_available_quantity(
                component, house.lot_stock_id, 100000.0
            )

        def make_order(tag, house):
            finished = self.env["product.product"].create(
                {"name": f"Allocation {tag}", "is_storable": True}
            )
            bom = self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": finished.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": component.id, "product_qty": 1.0})
                    ],
                }
            )
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "mrp_operation"), ("warehouse_id", "=", house.id)],
                limit=1,
            )
            values = {
                "product_id": finished.id,
                "bom_id": bom.id,
                "product_qty": 1.0,
            }
            if picking_type:
                values["picking_type_id"] = picking_type.id
            order = self.env["mrp.production"].create(values)
            order.action_confirm()
            return order, finished

        def demand(product, house, origins=None, raw_of=None, assign=False):
            move = self.env["stock.move"].create(
                {
                    "product_id": product.id,
                    "product_uom_qty": 1.0,
                    "location_id": house.lot_stock_id.id,
                    "location_dest_id": customers.id,
                    "company_id": house.company_id.id,
                    **(
                        {"move_orig_ids": [Command.set(origins.ids)]} if origins else {}
                    ),
                    **({"raw_material_production_id": raw_of.id} if raw_of else {}),
                }
            )
            move._action_confirm()
            if assign:
                move._action_assign()
            return move

        def finished_lines(order):
            return order.move_finished_ids.filtered(
                lambda m: m.product_id.is_storable and m.state != "cancel"
            )

        expected = {}

        free, free_product = make_order("free demand", warehouse)
        demand(free_product, warehouse)
        expected[free] = True

        nothing, _ = make_order("no demand", warehouse)
        expected[nothing] = False

        own_raw, own_raw_product = make_order("own raw move", warehouse)
        demand(own_raw_product, warehouse, raw_of=own_raw)
        expected[own_raw] = False

        elsewhere, elsewhere_product = make_order("demand elsewhere", warehouse)
        demand(elsewhere_product, other_warehouse)
        expected[elsewhere] = False

        chained, chained_product = make_order("chained to itself", warehouse)
        demand(chained_product, warehouse, origins=finished_lines(chained)[:1])
        expected[chained] = True

        borrower, borrower_product = make_order("chained elsewhere", warehouse)
        lender, _ = make_order("lends its line", warehouse)
        demand(borrower_product, warehouse, origins=finished_lines(lender)[:1])
        expected[borrower] = False
        expected[lender] = False

        chained_own, chained_own_product = make_order("chained and owned", warehouse)
        demand(
            chained_own_product,
            warehouse,
            origins=finished_lines(chained_own)[:1],
            raw_of=chained_own,
        )
        expected[chained_own] = False

        wrong_product, _ = make_order("chained wrong product", warehouse)
        demand(
            self.env["product.product"].create(
                {"name": "Allocation Unrelated", "is_storable": True}
            ),
            warehouse,
            origins=finished_lines(wrong_product)[:1],
        )
        expected[wrong_product] = False

        closed, closed_product = make_order("done with assigned", warehouse)
        self.env["stock.quant"]._update_available_quantity(
            closed_product, warehouse.lot_stock_id, 50.0
        )
        demand(closed_product, warehouse, assign=True)
        closed.qty_producing = closed.product_qty
        closed._update_moves_from_qty_producing()
        closed.button_mark_done()
        expected[closed] = True

        open_order, open_product = make_order("open with assigned", warehouse)
        self.env["stock.quant"]._update_available_quantity(
            open_product, warehouse.lot_stock_id, 50.0
        )
        demand(open_product, warehouse, assign=True)
        expected[open_order] = False

        second_house, second_product = make_order("second warehouse", other_warehouse)
        demand(second_product, other_warehouse)
        expected[second_house] = True

        orders = self.env["mrp.production"].union(*expected)
        self.env.flush_all()
        orders.invalidate_recordset(["show_allocation"])

        self.assertEqual(
            {order.product_id.name: order.show_allocation for order in orders},
            {order.product_id.name: value for order, value in expected.items()},
        )
        self.assertEqual(
            closed.state, "done", "the done-state scenario must really be done"
        )

    def test_operation_durations_are_sampled_in_one_query_for_the_whole_bom(self):
        workcenter = self.env["mrp.workcenter"].create({"name": "Sampling WC"})
        component, finished = self.env["product.product"].create(
            [
                {"name": "Sampling Component", "is_storable": True},
                {"name": "Sampling Finished", "is_storable": True},
            ]
        )
        batch_sizes = [10, 3, 1, 25]
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": f"sample op {index}",
                            "workcenter_id": workcenter.id,
                            "time_mode": "auto",
                            "time_mode_batch": size,
                        }
                    )
                    for index, size in enumerate(batch_sizes)
                ],
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        operations = bom.operation_ids
        origin = datetime(2026, 1, 1)
        for index, operation in enumerate(operations):
            for step in range([14, 9, 6, 4][index]):
                order = self.env["mrp.production"].create(
                    {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
                )
                workorder = order.workorder_ids.filtered(
                    lambda w, operation=operation: w.operation_id == operation
                )[:1]
                if not workorder:
                    continue
                if step % 5 == 0:
                    date_end = False
                elif step % 3 == 0:
                    date_end = origin
                else:
                    date_end = origin + timedelta(hours=step)
                workorder.write(
                    {
                        "state": "done",
                        "qty_produced": 1.0,
                        "duration": 10.0 + step,
                        "date_end": date_end,
                    }
                )
        self.env.flush_all()

        def per_operation_search():
            Workorder = self.env["mrp.workorder"]
            return {
                operation.id: Workorder.search(
                    [
                        ("operation_id", "in", operation.ids),
                        ("qty_produced", ">", 0),
                        ("state", "=", "done"),
                    ],
                    limit=operation.time_mode_batch,
                    order="date_end desc, id desc",
                ).ids
                for operation in operations
            }

        expected = per_operation_search()
        self.assertTrue(
            any(
                len(ids) == size
                for ids, size in zip(expected.values(), batch_sizes, strict=True)
            ),
            "the fixture must give at least one operation more history than its batch",
        )
        self.assertEqual(
            {
                key: value.ids
                for key, value in operations._get_recent_workorders().items()
            },
            expected,
            "the windowed sample must be the same rows, in the same order",
        )

        idle = self.env["mrp.routing.workcenter"].create(
            {
                "name": "sample op idle",
                "bom_id": bom.id,
                "workcenter_id": workcenter.id,
                "time_mode": "auto",
                "time_cycle_manual": 42.0,
            }
        )
        self.env.flush_all()
        self.assertEqual(
            idle._get_recent_workorders(), {idle.id: self.env["mrp.workorder"]}
        )
        self.assertEqual(idle.time_cycle, 42.0)

        all_operations = bom.operation_ids
        distinct_batches = set(all_operations.mapped("time_mode_batch"))
        self.assertGreater(len(all_operations), len(distinct_batches))
        sampling_queries = []
        original_execute = type(self.env.cr).execute

        def counting(cursor, query, params=None, log_exceptions=None):
            if "ROW_NUMBER() OVER" in str(query):
                sampling_queries.append(str(query))
            if log_exceptions is None:
                return original_execute(cursor, query, params)
            return original_execute(
                cursor, query, params, log_exceptions=log_exceptions
            )

        self.env.flush_all()
        all_operations.invalidate_recordset(["time_cycle"])
        self.patch(type(self.env.cr), "execute", counting)
        all_operations.mapped("time_cycle")
        self.assertEqual(
            len(sampling_queries),
            len(distinct_batches),
            f"{len(all_operations)} operations across {len(distinct_batches)} batch "
            f"sizes must cost {len(distinct_batches)} sampling queries",
        )

    def test_a_manufacturing_manager_is_not_narrowed_by_its_own_acl_row(self):
        manager = self.env["res.users"].create(
            {
                "name": "Rights Manager",
                "login": "audit_rights_manager",
                "group_ids": [Command.link(self.env.ref("mrp.group_mrp_manager").id)],
            }
        )
        self.assertTrue(manager.has_group("mrp.group_mrp_user"))
        for model in ("mrp.production", "resource.schedule.exception"):
            with self.subTest(model=model):
                scoped = self.env[model].with_user(manager)
                self.assertEqual(
                    {
                        operation: scoped.has_access(operation)
                        for operation in ("read", "write", "create", "unlink")
                    },
                    dict.fromkeys(("read", "write", "create", "unlink"), True),
                    f"a manufacturing manager must keep full rights on {model}",
                )

    def test_the_catalog_edits_a_bom_and_an_order_through_one_implementation(self):
        first, second, finished = self.env["product.product"].create(
            [
                {"name": "Catalog First", "is_storable": True},
                {"name": "Catalog Second", "is_storable": True, "standard_price": 3.5},
                {"name": "Catalog Finished", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": first.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 2.0}
        )

        for record, child_field, quantity_field in (
            (bom, "bom_line_ids", "product_qty"),
            (production, "move_raw_ids", "product_uom_qty"),
        ):
            with self.subTest(model=record._name):
                self.assertEqual(
                    record._update_order_line_info(
                        first.id, 7.0, child_field=child_field
                    ),
                    first.standard_price,
                )
                line = record[child_field].filtered(
                    lambda l, first=first: l.product_id == first
                )
                self.assertEqual(
                    line[quantity_field], 7.0, "an existing line is written"
                )

                self.assertEqual(
                    record._update_order_line_info(
                        second.id, 4.0, child_field=child_field
                    ),
                    3.5,
                    "the price of the product just added comes back",
                )
                added = record[child_field].filtered(
                    lambda l, second=second: l.product_id == second
                )
                self.assertEqual(
                    added[quantity_field], 4.0, "a new line keeps its quantity"
                )

                record._update_order_line_info(second.id, 0.0, child_field=child_field)
                self.assertFalse(
                    record[child_field].filtered(
                        lambda l, second=second: l.product_id == second
                    ),
                    "zero removes the line",
                )

                self.assertEqual(
                    record._update_order_line_info(first.id, 1.0),
                    0,
                    "without a child field there is nothing to edit",
                )
                self.assertEqual(
                    {
                        product.id: len(lines)
                        for product, lines in record._get_product_catalog_record_lines(
                            [first.id], child_field=child_field
                        ).items()
                    },
                    {first.id: 1},
                )

    def test_a_workorder_that_cannot_be_planned_says_why_and_where(self):
        empty_calendar = self.env["resource.calendar"].create(
            {"name": "Never Open", "attendance_ids": [Command.clear()]}
        )
        workcenter, alternative = self.env["mrp.workcenter"].create(
            [
                {"name": "Closed Center", "resource_calendar_id": empty_calendar.id},
                {"name": "Closed Backup", "resource_calendar_id": empty_calendar.id},
            ]
        )
        workcenter.alternative_workcenter_ids = [Command.set(alternative.ids)]
        component, finished = self.env["product.product"].create(
            [
                {"name": "Unplannable Component", "is_storable": True},
                {"name": "Unplannable Finished", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "closed op",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 60,
                        }
                    )
                ],
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
        )
        production.action_confirm()

        with self.assertRaises(UserError) as caught:
            production.button_plan()
        message = str(caught.exception)

        self.assertIn(production.workorder_ids.display_name, message)
        for candidate in (workcenter, alternative):
            self.assertIn(
                candidate.display_name,
                message,
                "every work centre that was tried has to be named",
            )
        self.assertIn(
            "No available slot",
            message,
            "the reason the slot search gave must reach the user",
        )

    def test_the_slot_sweep_refuses_a_workcenter_with_no_calendar(self):
        workcenter = self.env["mrp.workcenter"].create({"name": "Calendar Free"})
        workcenter.resource_calendar_id = False
        with self.assertRaises(UserError) as caught:
            workcenter._get_earliest_slot_and_reasons(
                datetime(2026, 1, 1, 8, 0), {workcenter: 60}
            )
        self.assertIn(workcenter.name, str(caught.exception))

    def test_the_slot_sweep_reports_having_no_workcenter_at_all(self):
        empty = self.env["mrp.workcenter"]
        best, reasons = empty._get_earliest_slot_and_reasons(
            datetime(2026, 1, 1, 8, 0), {}
        )
        self.assertIsNone(best)
        self.assertFalse(reasons)
        self.assertIn(
            "no work center", empty._prepare_unplannable_error("WO/1", reasons)
        )

    def test_work_order_efficiency_follows_the_duration_it_is_measured_against(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Efficiency Component", "is_storable": True},
                {"name": "Efficiency Finished", "is_storable": True},
            ]
        )
        workcenter = self.env["mrp.workcenter"].create({"name": "Efficiency WC"})
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "op",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 60,
                        }
                    )
                ],
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
        )
        production.action_confirm()
        workorder = production.workorder_ids
        workorder.duration = 30.0
        self.env.flush_all()

        workorder.duration_expected = 120.0
        self.env.flush_all()
        workorder.invalidate_recordset(["duration_percent"])
        self.assertEqual(
            workorder.duration_percent,
            75,
            "30 minutes against an expectation of 120 is 75%, not whatever the "
            "expectation used to be",
        )

    def test_an_unbuild_defaults_to_what_the_order_produced_however_it_is_created(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Unbuild Qty Component", "is_storable": True},
                {"name": "Unbuild Qty Finished", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 7.0}
        )
        production.action_confirm()
        warehouse = production.picking_type_id.warehouse_id
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 100.0
        )
        production.qty_producing = 7.0
        production._update_moves_from_qty_producing()
        production.button_mark_done()
        self.env.flush_all()
        self.assertEqual(production.qty_produced, 7.0)

        through_the_form = self.env["mrp.unbuild"].new({"mo_id": production.id})
        created = self.env["mrp.unbuild"].create({"mo_id": production.id})
        self.assertEqual(
            (created.product_qty, through_the_form.product_qty),
            (7.0, 7.0),
            "creating an unbuild must offer what the form offers",
        )

        self.assertEqual(
            self.env["mrp.unbuild"].create({"product_id": finished.id}).product_qty,
            1.0,
            "with no order to read, one unit is still the default",
        )
        self.assertEqual(
            self.env["mrp.unbuild"]
            .create({"mo_id": production.id, "product_qty": 3.0})
            .product_qty,
            3.0,
            "the field is readonly=False; an explicit quantity wins",
        )
        finished.tracking = "serial"
        self.env.flush_all()
        self.assertEqual(
            self.env["mrp.unbuild"].create({"mo_id": production.id}).product_qty,
            1.0,
            "a serial-tracked product is unbuilt one at a time",
        )

    def test_the_serial_badge_follows_the_tracking_it_asks_about(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Serial Badge Component", "is_storable": True},
                {
                    "name": "Serial Badge Finished",
                    "is_storable": True,
                    "tracking": "serial",
                },
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
        )
        production.lot_producing_ids = [
            Command.link(
                self.env["stock.lot"]
                .create({"name": "SERIAL-BADGE-1", "product_id": finished.id})
                .id
            )
        ]
        self.env.flush_all()
        self.assertEqual(production.serial_numbers_count, 1)

        finished.tracking = "lot"
        self.env.flush_all()
        self.assertEqual(
            production.serial_numbers_count,
            0,
            "a product that is no longer serial-tracked has no serial numbers to count",
        )

    def _serial_fixture(self, tag, quantity):
        component, finished = self.env["product.product"].create(
            [
                {"name": f"{tag} Component", "is_storable": True},
                {"name": f"{tag} Finished", "is_storable": True, "tracking": "serial"},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": quantity}
        )
        production.action_confirm()
        warehouse = production.picking_type_id.warehouse_id
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 1000.0
        )
        return production

    def test_serial_numbers_can_cover_less_than_the_whole_order(self):
        production = self._serial_fixture("Partial Serials", 5.0)
        wizard = self.env["mrp.production.serials"].create(
            {"production_id": production.id, "serial_numbers": "PART-1"}
        )
        wizard.action_split_and_assign_serials()

        orders = production.production_group_id.production_ids
        self.assertEqual(
            [
                (order.product_qty, order.lot_producing_ids.mapped("name"))
                for order in orders
            ],
            [(1.0, ["PART-1"]), (4.0, [])],
            "the serial takes one unit and the rest stays as one unserialised order",
        )

    def test_a_serial_typed_twice_is_folded_once_everywhere(self):
        production = self._serial_fixture("Repeated Serials", 3.0)
        wizard = self.env["mrp.production.serials"].create(
            {"production_id": production.id, "serial_numbers": "DUP-1\nDUP-1\nDUP-2"}
        )
        self.assertEqual(wizard._get_names_from_serial_numbers(), ["DUP-1", "DUP-2"])
        self.assertEqual(
            wizard._get_or_create_lots().mapped("name"),
            ["DUP-1", "DUP-2"],
            "a repeat must not try to create the same serial twice",
        )
        wizard._onchange_serial_numbers()
        self.assertEqual(wizard.serial_numbers, "DUP-1\nDUP-2")

        wizard.action_split_and_assign_serials()
        orders = production.production_group_id.production_ids
        self.assertEqual(
            sorted(orders.lot_producing_ids.mapped("name")), ["DUP-1", "DUP-2"]
        )

    def test_setting_the_consumed_quantity_is_decided_by_the_total(self):
        component, finished = self.env["product.product"].create(
            [
                {"name": "Consumption Component", "is_storable": True},
                {"name": "Consumption Finished", "is_storable": True},
            ]
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "consumption": "warning",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 4.0})
                ],
            }
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "bom_id": bom.id, "product_qty": 1.0}
        )
        production.action_confirm()
        warehouse = production.picking_type_id.warehouse_id
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 1000.0
        )
        original = production.move_raw_ids
        original.product_uom_qty = 1.0
        self.env["stock.move"].create(
            {
                "product_id": component.id,
                "product_uom_qty": 1.0,
                "quantity": 1.0,
                "picked": True,
                "raw_material_production_id": production.id,
                "additional": True,
                "location_id": original.location_id.id,
                "location_dest_id": original.location_dest_id.id,
                "company_id": production.company_id.id,
                "product_uom_id": component.uom_id.id,
            }
        )._action_confirm()
        production.qty_producing = 1.0
        production._update_moves_from_qty_producing()
        self.env.flush_all()

        issues = production._get_consumption_issues()
        self.assertTrue(issues, "the fixture must under-consume against its BoM")
        action = production._prepare_action_consumption_wizard(issues)
        wizard = (
            self.env[action["res_model"]].with_context(**action["context"]).create({})
        )
        self.patch(type(wizard), "action_confirm", lambda self: None)
        wizard.action_set_qty()
        self.env.flush_all()

        quantities = sorted(production.move_raw_ids.mapped("quantity"))
        self.assertEqual(
            quantities,
            [0.0, 4.0],
            "the whole expected quantity goes on one move, the others are cleared",
        )
        self.assertEqual(sum(quantities), 4.0, "and the total is what the BoM expects")
        self.assertTrue(
            all(production.move_raw_ids.mapped("picked")),
            "every matching move is marked picked, cleared or not",
        )

    def test_exploding_many_moves_of_one_kit_resolves_it_once(self):
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        customers = self.env.ref("stock.stock_location_customers")
        leaves = self.env["product.product"].create(
            [
                {"name": f"Explode Leaf {index}", "is_storable": True}
                for index in range(3)
            ]
        )
        nested, kit = self.env["product.product"].create(
            [
                {"name": "Explode Nested Kit", "is_storable": True},
                {"name": "Explode Kit", "is_storable": True},
            ]
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": nested.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create({"product_id": leaf.id, "product_qty": 1.0})
                        for leaf in leaves
                    ],
                },
                {
                    "product_tmpl_id": kit.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create({"product_id": nested.id, "product_qty": 1.0}),
                        Command.create(
                            {"product_id": leaves[0].id, "product_qty": 2.0}
                        ),
                    ],
                },
            ]
        )
        self.env.flush_all()

        def queries_for(count):
            picking = self.env["stock.picking"].create(
                {
                    "picking_type_id": warehouse.out_type_id.id,
                    "location_id": warehouse.lot_stock_id.id,
                    "location_dest_id": customers.id,
                }
            )
            moves = self.env["stock.move"].create(
                [
                    {
                        "product_id": kit.id,
                        "product_uom_qty": 1.0,
                        "picking_id": picking.id,
                        "location_id": warehouse.lot_stock_id.id,
                        "location_dest_id": customers.id,
                        "company_id": warehouse.company_id.id,
                    }
                    for _ in range(count)
                ]
            )
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            exploded = moves.action_explode()
            self.env.flush_all()
            self.assertTrue(exploded, "the fixture must actually explode")
            return self.env.cr.sql_statement_count - before

        few = queries_for(2)
        many = queries_for(20)
        per_move = (many - few) / 18
        self.assertLess(
            per_move,
            1.0,
            "exploding a kit must not cost a query per move: "
            f"{few} queries for 2 moves, {many} for 20, {per_move:.2f} per move",
        )

    def test_posting_the_rest_of_an_order_keeps_the_first_batch_traceable(self):
        """`_post_inventory` runs once per post, `move_finished_ids` spans them all.

        Produce part of an order, post it, then mark the rest done. The first
        batch's produced line is already linked to what it consumed, and the
        second pass must not reach back and rewrite it -- least of all with the
        empty set it holds when the raw moves were consumed in full the first
        time round.
        """
        finished = self.env["product.product"].create(
            {"name": "Partial finished", "is_storable": True, "route_ids": []}
        )
        component = self.env["product.product"].create(
            {"name": "Partial component", "is_storable": True}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1.0})
                ],
            }
        )
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 100.0
        )
        production = self.env["mrp.production"].create(
            {"product_id": finished.id, "product_qty": 10.0, "bom_id": bom.id}
        )
        production.action_confirm()
        production.action_assign()

        production.qty_producing = 4.0
        production.move_raw_ids.picked = True
        production._post_inventory()

        first_batch = production.move_finished_ids.move_line_ids.filtered(
            lambda line: line.move_id.state == "done"
        )
        self.assertEqual(len(first_batch), 1)
        traced = first_batch.consume_line_ids
        self.assertTrue(
            traced, "the first batch must record what it consumed to be a test at all"
        )

        production.qty_producing = 10.0
        production.move_raw_ids.filtered(lambda m: m.state != "done").picked = True
        production.button_mark_done()
        self.env.invalidate_all()

        self.assertEqual(
            first_batch.consume_line_ids,
            traced,
            "posting the rest of the order rewrote what the first batch consumed",
        )
