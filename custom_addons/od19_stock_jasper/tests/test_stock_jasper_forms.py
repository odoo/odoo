import os

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

MODULE = "od19_stock_jasper"


@tagged("post_install", "-at_install")
class StockJasperCase(TransactionCase):
    """Shared helpers for the Stock domain Jasper print forms."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.product = cls.env["product.product"].create(
            {"name": "Jasper Test Product", "is_storable": True}
        )
        cls.department = cls.env["hr.department"].create(
            {"name": "Jasper Test Dept", "code": "IA"}
        )

    def _picking_type(self, code):
        ptype = self.env["stock.picking.type"].search(
            [("code", "=", code)], limit=1
        )
        if not ptype and code == "internal":
            # This database has no warehouse internal transfer type yet.
            ptype = self.env["stock.picking.type"].create(
                {
                    "name": "Internal Transfers",
                    "code": "internal",
                    "sequence_code": "INT",
                    "default_location_src_id": self.stock_location.id,
                    "default_location_dest_id": self.stock_location.id,
                }
            )
        return ptype

    def _make_picking(self, code, **extra):
        ptype = self._picking_type(code)
        fallback = {
            "incoming": (self.supplier_location, self.stock_location),
            "outgoing": (self.stock_location, self.customer_location),
            "internal": (self.stock_location, self.stock_location),
        }.get(code, (self.stock_location, self.stock_location))
        vals = {
            "picking_type_id": ptype.id,
            "location_id": (ptype.default_location_src_id or fallback[0]).id,
            "location_dest_id": (
                ptype.default_location_dest_id or fallback[1]
            ).id,
        }
        if code == "outgoing":
            # Enforced by od19_delivery_label on outgoing deliveries.
            vals["od19_department_code"] = self.department.code
        vals.update(extra)
        return self.env["stock.picking"].create(vals)

    def _assert_wizard_defaults(self, model, jasper_basename, view_xmlid):
        """A wizard must point at its .jasper file and default form view."""
        report = self.env[model].create({})
        self.assertTrue(
            report.jasper_file.endswith(jasper_basename), report.jasper_file
        )
        self.assertTrue(
            os.path.isfile(report.get_jrxml_file()), report.get_jrxml_file()
        )
        view = self.env[model].get_views([[False, "form"]])["views"]["form"]
        self.assertEqual(view["id"], self.env.ref(view_xmlid).id)


@tagged("post_install", "-at_install")
class TestDeliveryReport(StockJasperCase):
    """F-IV-002 Delivery Order Form (ใบส่งของ) - outgoing only."""

    def _report(self, picking=True, **values):
        report = self.env["delivery.report"].create(values)
        if picking:
            report = report.with_context(active_ids=picking.ids)
        return report

    def test_defaults(self):
        self._assert_wizard_defaults(
            "delivery.report",
            "delivery_report.jasper",
            "%s.view_delivery_report" % MODULE,
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report(self._make_picking("outgoing"))
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Receive_No"],
            "WHERE sp.id in (%s)" % report.env.context["active_ids"][0],
        )
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertTrue(parameters["p_Path"].endswith("/"))

    def test_locale_follows_date_type(self):
        report = self._report(self._make_picking("outgoing"), date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_non_outgoing_picking_raises(self):
        with self.assertRaises(ValidationError):
            self._report(self._make_picking("incoming")).get_parameters()

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(picking=False).get_parameters()


@tagged("post_install", "-at_install")
class TestReceiveReport(StockJasperCase):
    """F-IV-001 Goods Receipt Form (ใบรับสินค้า) - incoming only."""

    def _report(self, picking=True, **values):
        report = self.env["receive.report"].create(values)
        if picking:
            report = report.with_context(active_ids=picking.ids)
        return report

    def test_defaults(self):
        self._assert_wizard_defaults(
            "receive.report",
            "receive_report.jasper",
            "%s.view_receive_report" % MODULE,
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report(self._make_picking("incoming"))
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Receive_No"],
            "WHERE sp.id in (%s)" % report.env.context["active_ids"][0],
        )
        self.assertEqual(parameters["p_locale"], "en")

    def test_non_incoming_picking_raises(self):
        with self.assertRaises(ValidationError):
            self._report(self._make_picking("outgoing")).get_parameters()

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(picking=False).get_parameters()


@tagged("post_install", "-at_install")
class TestInternalTransferReport(StockJasperCase):
    """Internal Transfer Form (ใบโอนย้ายภายใน) - internal only."""

    def _report(self, picking=True, **values):
        report = self.env["internal.transfer.report"].create(values)
        if picking:
            report = report.with_context(active_ids=picking.ids)
        return report

    def test_defaults(self):
        self._assert_wizard_defaults(
            "internal.transfer.report",
            "internal_transfer_report.jasper",
            "%s.view_internal_transfer_report" % MODULE,
        )

    def test_parameters_follow_legacy_contract(self):
        report = self._report(self._make_picking("internal"))
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Receive_No"],
            "WHERE sp.id in (%s)" % report.env.context["active_ids"][0],
        )
        self.assertEqual(parameters["p_locale"], "en")

    def test_non_internal_picking_raises(self):
        with self.assertRaises(ValidationError):
            self._report(self._make_picking("outgoing")).get_parameters()

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(picking=False).get_parameters()


@tagged("post_install", "-at_install")
class TestReturnReport(StockJasperCase):
    """Goods Return Form (ใบส่งคืน) - requires a returned move."""

    def _report(self, picking=True, **values):
        report = self.env["return.report"].create(values)
        if picking:
            report = report.with_context(active_ids=picking.ids)
        return report

    def _add_move(self, picking):
        return self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "picking_id": picking.id,
            }
        )

    def test_defaults(self):
        self._assert_wizard_defaults(
            "return.report",
            "return_report.jasper",
            "%s.view_return_report" % MODULE,
        )

    def test_picking_without_returned_move_raises(self):
        picking = self._make_picking("outgoing")
        self._add_move(picking)
        with self.assertRaises(ValidationError):
            self._report(picking).get_parameters()

    def test_parameters_follow_legacy_contract(self):
        report = self._report(self._make_picking("outgoing"))
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Receive_No"],
            "WHERE sp.id in (%s)" % report.env.context["active_ids"][0],
        )
        self.assertEqual(parameters["p_locale"], "en")

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(picking=False).get_parameters()


@tagged("post_install", "-at_install")
class TestGoodsIssuePickingReport(StockJasperCase):
    """Goods Issue Form (ใบเบิกสินค้า) - requires an issue reason."""

    def _report(self, picking=True, **values):
        report = self.env["goods.issue.picking.report"].create(values)
        if picking:
            report = report.with_context(active_ids=picking.ids)
        return report

    def test_defaults(self):
        self._assert_wizard_defaults(
            "goods.issue.picking.report",
            "goods_issue_picking_report.jasper",
            "%s.view_goods_issue_picking_report" % MODULE,
        )

    def test_picking_without_issue_reason_raises(self):
        with self.assertRaises(ValidationError):
            self._report(self._make_picking("outgoing")).get_parameters()

    def test_parameters_when_issue_reason_is_set(self):
        picking = self._make_picking(
            "outgoing", od19_goods_issue_reason="เบิกใช้ในแผนก"
        )
        parameters = self._report(picking).get_parameters()
        self.assertEqual(
            parameters["p_Receive_No"],
            "WHERE sp.id in (%s)" % picking.id,
        )
        self.assertEqual(parameters["p_locale"], "en")

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(picking=False).get_parameters()


@tagged("post_install", "-at_install")
class TestProductAndLocationLabels(StockJasperCase):
    """Barcode / QR label wizards (product, lot/serial, location)."""

    LABELS = [
        (
            "product.barcode.report",
            "product_barcode_report.jasper",
            "view_product_barcode_report",
            "WHERE pt.id in",
        ),
        (
            "product.qrcode.report",
            "product_qrcode_report.jasper",
            "view_product_qrcode_report",
            "WHERE pt.id in",
        ),
        (
            "product.lot.barcode.report",
            "product_lot_barcode_report.jasper",
            "view_product_lot_barcode_report",
            "WHERE pd.id in",
        ),
        (
            "product.lot.qrcode.report",
            "product_lot_qrcode_report.jasper",
            "view_product_lot_qrcode_report",
            "WHERE pd.id in",
        ),
        (
            "location.barcode.report",
            "location_barcode_report.jasper",
            "view_location_barcode_report",
            "WHERE st.id in",
        ),
        (
            "location.qrcode.report",
            "location_qrcode_report.jasper",
            "view_location_qrcode_report",
            "WHERE st.id in",
        ),
    ]

    def test_label_wizards_point_at_their_jasper_file_and_view(self):
        for model, jasper_basename, view_xmlid, _where in self.LABELS:
            self._assert_wizard_defaults(
                model, jasper_basename, "%s.%s" % (MODULE, view_xmlid)
            )

    def test_label_parameters_and_locale(self):
        for model, _jasper, _view, where in self.LABELS:
            report = self.env[model].create({}).with_context(active_ids=[1])
            parameters = report.get_parameters()
            self.assertEqual(parameters["p_Where"], "%s (1)" % where)
            self.assertEqual(parameters["p_Print"], "1")
            self.assertEqual(report.get_locale(), "en_EN")


@tagged("post_install", "-at_install")
class TestInventoryJasperReports(StockJasperCase):
    """Inventory reporting wizards ported from ``dtr_stock_report``.

    Covers the Stock Card, Product Moves, Inventory Valuation and the
    Special / Aging / Dead Stock variants (legacy F-IV-001 .. F-IV-008).
    """

    # (model, jasper basename, form view xmlid, create vals, p_Where sentinel)
    WIZARDS = [
        (
            "stock.card.report",
            "stock_card_report.jasper",
            "view_stock_card_report",
            {},
            "WHERE svl.company_id=",
        ),
        (
            "inventory.move.report",
            "inventory_move_report.jasper",
            "view_inventory_move_report",
            "wh",
            "CAST(move.date AS date)",
        ),
        (
            "inventory.valuation.report",
            "inventory_valuation_report.jasper",
            "view_inventory_valuation_report",
            {},
            None,
        ),
        (
            "inventory.move.special.report",
            "inventory_move_special_report.jasper",
            "view_inventory_move_special_report",
            {},
            "sm.state='done'",
        ),
        (
            "inventory.valuation.special.report",
            "inventory_valuation_special_report.jasper",
            "view_inventory_valuation_special_report",
            {},
            "sm.state='done'",
        ),
        (
            "inventory.move.aging.report",
            "inventory_move_aging_report.jasper",
            "view_inventory_move_aging_report",
            {},
            "sm.state='done'",
        ),
        (
            "inventory.valuation.aging.report",
            "inventory_valuation_aging_report.jasper",
            "view_inventory_valuation_aging_report",
            {},
            "sm.state='done'",
        ),
        (
            "dead.stock.report",
            "dead_stock_report.jasper",
            "view_dead_stock_report",
            {},
            "a.company_id",
        ),
    ]

    def _create_vals(self, needs_location):
        """Product Moves requires a location before it can be created."""
        if needs_location == "wh":
            return {"wh": self.stock_location.id}
        return {}

    def test_wizards_point_at_their_jasper_file_and_view(self):
        for model, basename, view_xmlid, vals, _where in self.WIZARDS:
            report = self.env[model].create(self._create_vals(vals))
            self.assertTrue(
                report.jasper_file.endswith(basename), report.jasper_file
            )
            self.assertTrue(
                os.path.isfile(report.get_jrxml_file()),
                report.get_jrxml_file(),
            )
            view = self.env[model].get_views([[False, "form"]])["views"]["form"]
            self.assertEqual(
                view["id"], self.env.ref("%s.%s" % (MODULE, view_xmlid)).id
            )

    def test_parameters_follow_legacy_contract(self):
        for model, _basename, _view, vals, where in self.WIZARDS:
            report = self.env[model].create(self._create_vals(vals))
            parameters = report.get_parameters()
            self.assertEqual(parameters["p_language"], "thai")
            self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
            self.assertEqual(parameters["p_locale"], "en")
            if where:
                self.assertIn(where, parameters["p_Where"])

    def test_locale_follows_date_type(self):
        report = self.env["stock.card.report"].create({"date_type": "BE"})
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_aging_wizards_expose_day_range(self):
        move = self.env["inventory.move.aging.report"].create({})
        self.assertEqual(move.get_parameters()["p_Days"], "30")
        valuation = self.env["inventory.valuation.aging.report"].create({})
        self.assertEqual(valuation.get_parameters()["p_Days"], "30")
        dead = self.env["dead.stock.report"].create({})
        self.assertEqual(dead.get_parameters()["p_days"], "30")

    def test_stock_card_product_filter(self):
        report = self.env["stock.card.report"].create(
            {"p_Product": [(6, 0, [self.product.id])]}
        )
        self.assertIn(
            "AND svl.product_id in (%s)" % self.product.id,
            report.get_parameters()["p_Where"],
        )

    def test_move_report_exposes_location_scope(self):
        report = self.env["inventory.move.report"].create(
            {"wh": self.stock_location.id}
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Location_ID"], str(self.stock_location.id))
        self.assertIn(str(self.stock_location.id), parameters["p_location_ids"])

    def test_valuation_report_exposes_filter_fragments(self):
        report = self.env["inventory.valuation.report"].create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_WhereProduct"], "")
        self.assertEqual(parameters["p_WhereLocation"], "")
        self.assertEqual(parameters["p_WhereLot"], "")
        self.assertEqual(parameters["p_CompanyId"], str(self.env.company.id))

    def test_dead_stock_location_filter(self):
        report = self.env["dead.stock.report"].create(
            {"p_location": [(6, 0, [self.stock_location.id])]}
        )
        parameters = report.get_parameters()
        self.assertIn(
            "q.location_id in (%s)" % self.stock_location.id,
            parameters["p_location_src_id"],
        )
        self.assertEqual(parameters["p_Print_By"], self.env.user.name)


@tagged("post_install", "-at_install")
class TestStockCardVariants(StockJasperCase):
    """Stock Card sub-views ported from ``dtr_stock_report``.

    The legacy product card ships six views (PO / SO / PO return / SO return /
    stock moving); every view filters by product and as-of date.
    """

    # (model, jasper basename, form view xmlid, needs location?)
    VARIANTS = [
        (
            "stock.card.po.report",
            "stock_card_po_report.jasper",
            "view_stock_card_po_report",
            False,
        ),
        (
            "stock.card.so.report",
            "stock_card_so_report.jasper",
            "view_stock_card_so_report",
            False,
        ),
        (
            "stock.card.po.return.report",
            "stock_card_po_return_report.jasper",
            "view_stock_card_po_return_report",
            False,
        ),
        (
            "stock.card.so.return.report",
            "stock_card_so_return_report.jasper",
            "view_stock_card_so_return_report",
            False,
        ),
        (
            "stock.card.stock.moving.report",
            "stock_card_stock_moving_report.jasper",
            "view_stock_card_stock_moving_report",
            True,
        ),
    ]

    def _create_vals(self, needs_location):
        vals = {"p_Product_No": self.product.id}
        if needs_location:
            vals["p_WH_No"] = self.stock_location.id
        return vals

    def test_variants_point_at_their_jasper_file_and_view(self):
        for model, basename, view_xmlid, needs_location in self.VARIANTS:
            report = self.env[model].create(self._create_vals(needs_location))
            self.assertTrue(
                report.jasper_file.endswith(basename), report.jasper_file
            )
            self.assertTrue(
                os.path.isfile(report.get_jrxml_file()),
                report.get_jrxml_file(),
            )
            view = self.env[model].get_views([[False, "form"]])["views"]["form"]
            self.assertEqual(
                view["id"], self.env.ref("%s.%s" % (MODULE, view_xmlid)).id
            )

    def test_variants_pass_product_and_as_of_date(self):
        for model, _basename, _view, needs_location in self.VARIANTS:
            report = self.env[model].create(self._create_vals(needs_location))
            parameters = report.get_parameters()
            self.assertEqual(parameters["p_Product_No"], str(self.product.id))
            self.assertEqual(
                parameters["p_Date_As_Off"], str(report.p_Date_As_Off)
            )

    def test_stock_moving_passes_location(self):
        report = self.env["stock.card.stock.moving.report"].create(
            {
                "p_Product_No": self.product.id,
                "p_WH_No": self.stock_location.id,
            }
        )
        self.assertEqual(
            report.get_parameters()["p_WH_No"], str(self.stock_location.id)
        )


@tagged("post_install", "-at_install")
class TestPickingDocumentReports(StockJasperCase):
    """Delivery Order report and Picking List - driven by selected pickings."""

    # (model, jasper basename, form view xmlid)
    REPORTS = [
        (
            "delivery.order.report",
            "delivery_order_report.jasper",
            "view_delivery_order_report",
        ),
        (
            "picking.list.report",
            "picking_list_report.jasper",
            "view_picking_list_report",
        ),
    ]

    def test_defaults(self):
        for model, basename, view_xmlid in self.REPORTS:
            self._assert_wizard_defaults(
                model, basename, "%s.%s" % (MODULE, view_xmlid)
            )

    def test_ids_fragment_from_selected_pickings(self):
        picking = self._make_picking("outgoing")
        for model, _basename, _view in self.REPORTS:
            report = self.env[model].create({}).with_context(
                active_ids=picking.ids
            )
            self.assertEqual(
                report.get_parameters()["ids"],
                "where sp.id in (%s)" % picking.id,
            )

    def test_no_document_selected_raises(self):
        for model, _basename, _view in self.REPORTS:
            with self.assertRaises(UserError):
                self.env[model].create({}).get_parameters()


@tagged("post_install", "-at_install")
class TestQcInspectionReport(StockJasperCase):
    """QC Inspection (ใบตรวจสอบคุณภาพ) re-targeted onto ``od19.qc.inspection``."""

    def _inspection(self, **values):
        vals = {"product_id": self.product.id}
        vals.update(values)
        return self.env["od19.qc.inspection"].create(vals)

    def _report(self, inspections=None, **values):
        report = self.env["qc.inspection.report"].create(values)
        if inspections:
            report = report.with_context(active_ids=inspections.ids)
        return report

    def test_defaults(self):
        self._assert_wizard_defaults(
            "qc.inspection.report",
            "qc_inspection_report.jasper",
            "%s.view_qc_inspection_report" % MODULE,
        )

    def test_parameters_follow_legacy_contract(self):
        inspection = self._inspection(name="QC-JASPER-1")
        report = self._report(inspection)
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_Receive_No"],
            "WHERE qc.name in ('QC-JASPER-1')",
        )
        self.assertEqual(parameters["p_Company_No"], str(self.env.company.id))
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertTrue(parameters["p_Path"].endswith("/"))

    def test_locale_follows_date_type(self):
        report = self._report(self._inspection(), date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_no_document_selected_raises(self):
        with self.assertRaises(UserError):
            self._report(inspections=False).get_parameters()
