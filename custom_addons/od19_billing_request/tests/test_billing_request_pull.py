from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestPull(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Pull Customer"})
        cls.vendor = cls.env["res.partner"].create({"name": "Pull Vendor"})
        # ``service`` avoids creating a delivery picking on confirm
        # (od19_delivery_label requires a DEPT code on those pickings).
        cls.product = cls.env["product.product"].create(
            {"name": "Pull Item", "type": "service", "list_price": 20.0}
        )
        cls.product.invoice_policy = "order"
        cls.product.purchase_method = "purchase"

    def _confirmed_so(self, qty=5.0):
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": 20.0,
                            "name": self.product.name,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        return so

    def test_pull_from_sale_order(self):
        so = self._confirmed_so()
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        request.origin_ref = so
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "od19.billing.request",
                "res_id": request.id,
                "source_ref": "sale.order,%s" % so.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.sale_line_id, so.order_line)
        self.assertAlmostEqual(request.line_ids.price_unit, 20.0)

    def test_pull_from_purchase_order(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 3.0,
                            "price_unit": 15.0,
                            "name": self.product.name,
                            "date_planned": "2026-11-10 00:00:00",
                        },
                    )
                ],
            }
        )
        # ``button_confirm`` is gated by the procurement approval flow
        # (od19_purchase_procurement_core): a PO must be approved first.
        po.action_od19_submit_for_approval()
        po.action_od19_approve()
        po.button_confirm()
        request = self.env["od19.billing.request"].create({"direction": "ap"})
        request.origin_ref = po
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "od19.billing.request",
                "res_id": request.id,
                "source_ref": "purchase.order,%s" % po.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.purchase_line_id, po.order_line)

    def test_remove_bound_source_lines(self):
        so = self._confirmed_so()
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        request.origin_ref = so
        request._od19_pull_apply(so, so.order_line)
        self.assertEqual(len(request.line_ids), 1)
        removed = request._od19_pull_remove(so)
        self.assertEqual(removed, 1)
        self.assertFalse(request.line_ids)

    def test_wizard_line_res_model_is_line_model(self):
        so = self._confirmed_so()
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        request.origin_ref = so
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "od19.billing.request",
                "res_id": request.id,
                "source_ref": "sale.order,%s" % so.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(wizard.line_ids.res_model, "sale.order.line")

    def test_duplicate_pull_is_excluded(self):
        so = self._confirmed_so()
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        request.origin_ref = so
        request._od19_pull_apply(so, so.order_line)
        self.assertFalse(request._od19_pull_candidate_lines(so))

    def test_select_mode_pulls_only_selected(self):
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "price_unit": 20.0,
                            "name": self.product.name,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 3.0,
                            "price_unit": 20.0,
                            "name": self.product.name,
                        },
                    ),
                ],
            }
        )
        so.action_confirm()
        request = self.env["od19.billing.request"].create({"direction": "ar"})
        request.origin_ref = so
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "od19.billing.request",
                "res_id": request.id,
                "source_ref": "sale.order,%s" % so.id,
                "mode": "select",
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 2)
        first = wizard.line_ids[0]
        wizard.line_ids.write({"selected": False})
        first.selected = True
        wizard.action_pull()
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.sale_line_id, first._od19_get_source_line())
