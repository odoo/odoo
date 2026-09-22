from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.stock.tests.common import TestStockCommon


@tagged("post_install", "-at_install")
class TestTraceabilityFormulaReport(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("stock.stock_traceability_report")
        cls.tracked = cls.env["product.product"].create(
            {"name": "Traced", "is_storable": True, "tracking": "lot"}
        )
        cls.lot = cls.env["stock.lot"].create(
            {"name": "LOT-TRC", "product_id": cls.tracked.id}
        )

    def _done_move_line(self, src, dst, date):
        move = self.env["stock.move"].create(
            {
                "product_id": self.tracked.id,
                "product_uom_qty": 5,
                "location_id": src.id,
                "location_dest_id": dst.id,
            }
        )
        line = self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.tracked.id,
                "lot_id": self.lot.id,
                "location_id": src.id,
                "location_dest_id": dst.id,
                "quantity": 5,
            }
        )
        move.state = "done"
        line.date = date
        move.date = date
        return line

    def _chain(self):
        return (
            self._done_move_line(
                self.supplier_location, self.stock_location, datetime(2026, 1, 1)
            ),
            self._done_move_line(
                self.stock_location, self.shelf_1, datetime(2026, 2, 1)
            ),
            self._done_move_line(
                self.shelf_1, self.customer_location, datetime(2026, 3, 1)
            ),
        )

    def _options(self, **context):
        return self.report.with_context(**context).get_options(
            {"selected_variant_id": self.report.id}
        )

    def _columns(self, line):
        return {
            column["expression_label"]: column["name"] for column in line["columns"]
        }

    def test_a_lot_lists_its_done_move_lines_newest_first(self):
        self._chain()
        options = self._options(active_model="stock.lot", active_id=self.lot.id)
        lines = self.report._get_lines(options)
        self.assertEqual(
            [self._columns(line)["location_destination"] for line in lines],
            [
                self.customer_location.display_name,
                self.shelf_1.display_name,
                self.stock_location.display_name,
            ],
        )
        self.assertEqual({self._columns(line)["lot"] for line in lines}, {"LOT-TRC"})
        self.assertFalse(options["filters"]["show_date"])

    def test_a_picking_line_unfolds_into_what_came_before_it(self):
        _receipt, _internal, delivery = self._chain()
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.shelf_1.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        delivery.move_id.picking_id = picking
        options = self._options(active_model="stock.picking", active_id=picking.id)
        options["unfold_all"] = True
        lines = self.report._get_lines(options)
        by_level = [
            (line["level"], self._columns(line)["location_source"]) for line in lines
        ]
        self.assertEqual(by_level[0], (1, self.shelf_1.display_name))
        self.assertIn((2, self.stock_location.display_name), by_level)
        self.assertTrue(
            all(line["parent_id"] for line in lines if line["level"] > 1),
            "the upstream lines are children of the line they explain",
        )

    def test_the_carets_open_the_records_of_a_line(self):
        _receipt, _internal, delivery = self._chain()
        options = self._options(active_model="stock.lot", active_id=self.lot.id)
        line_id = self.report._get_generic_line_id("stock.move.line", delivery.id)
        lot_action = self.report.dispatch_report_action(
            options, "caret_option_open_traceability_lot", {"line_id": line_id}
        )
        self.assertEqual(
            (lot_action["res_model"], lot_action["res_id"]), ("stock.lot", self.lot.id)
        )
        stream = self.report.dispatch_report_action(
            options, "caret_option_open_traceability_stream", {"line_id": line_id}
        )
        self.assertEqual(stream["context"]["active_id"], delivery.id)
        self.assertTrue(stream["context"]["auto_unfold"])
        with self.assertRaises(UserError):
            self.report.dispatch_report_action(
                options, "caret_option_open_traceability_partner", {"line_id": line_id}
            )

    def test_the_form_buttons_open_the_formula_report(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_report"
        )
        self.assertEqual(action["tag"], "account_report")
        context = self.env["ir.actions.actions"]._eval_action_context(action["context"])
        self.assertEqual(context["report_id"], self.report.id)
