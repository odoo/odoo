from odoo.tests.common import TransactionCase


class TestThreeWayMatch(TransactionCase):
    """3-way matching (PO + รับของ + ใบแจ้งหนี้) สำหรับสินค้าคงคลัง.

    Odoo 19 CE ควบคุมการออกบิลผู้ขายด้วย ``product.purchase_method``:

    * ``receive`` — ออกบิลได้เฉพาะของที่ **รับแล้ว** (3-way matching)
    * ``purchase`` — ออกบิลตามจำนวนที่สั่ง (2-way matching)

    สินค้าคงคลัง (Goods) ตั้งต้นที่ ``receive`` และงานบริการถูกบังคับให้เป็น
    ``purchase`` เสมอ (ดู ``purchase/models/product.py``)
    """

    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Three Way Vendor", "company_type": "company"}
        )
        manager_group = self.env.ref("purchase.group_purchase_manager")
        base_user_group = self.env.ref("base.group_user")
        self.manager = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Three Way Purchase Manager",
                    "login": "three.way.manager@example.com",
                    "email": "three.way.manager@example.com",
                    "company_id": self.env.company.id,
                    "company_ids": [(6, 0, [self.env.company.id])],
                    "group_ids": [(6, 0, [base_user_group.id, manager_group.id])],
                }
            )
        )
        self.goods = self.env["product.product"].create(
            {
                "name": "Three Way Goods",
                "purchase_ok": True,
                "type": "consu",
                "is_storable": True,
            }
        )
        self.service = self.env["product.product"].create(
            {
                "name": "Three Way Service",
                "purchase_ok": True,
                "type": "service",
            }
        )

    def _make_order(self, product, qty, price_unit=100.0):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": product.display_name,
                "product_id": product.id,
                "product_qty": qty,
                "price_unit": price_unit,
                "product_uom_id": product.uom_id.id,
                "date_planned": "2026-11-01 00:00:00",
                "tax_ids": False,
            }
        )
        order.action_od19_submit_for_approval()
        order.with_user(self.manager).action_od19_approve()
        order.button_confirm()
        self.assertEqual(order.state, "purchase")
        return order

    def _receive(self, order, qty):
        picking = order.picking_ids.filtered(lambda p: p.state != "done")
        picking.move_ids.quantity = qty
        picking.move_ids.picked = True
        picking.with_context(skip_backorder=True).button_validate()

    # ------------------------------------------------------------------
    # Control policy (ค่าเริ่มต้นของ Odoo 19 CE)
    # ------------------------------------------------------------------
    def test_goods_default_to_receive_and_services_to_purchase(self):
        new_goods = self.env["product.product"].create(
            {
                "name": "New Storable Goods",
                "purchase_ok": True,
                "type": "consu",
                "is_storable": True,
            }
        )
        new_service = self.env["product.product"].create(
            {
                "name": "New Service",
                "purchase_ok": True,
                "type": "service",
            }
        )
        self.assertEqual(new_goods.purchase_method, "receive")
        self.assertEqual(self.goods.purchase_method, "receive")
        self.assertEqual(new_service.purchase_method, "purchase")
        self.assertEqual(self.service.purchase_method, "purchase")

    # ------------------------------------------------------------------
    # 3-way match: สินค้าคงคลัง
    # ------------------------------------------------------------------
    def test_goods_cannot_be_billed_before_receipt(self):
        order = self._make_order(self.goods, 10)
        line = order.order_line
        self.assertEqual(line.qty_received, 0.0)
        self.assertEqual(line.qty_to_invoice, 0.0)
        self.assertEqual(order.invoice_status, "no")

    def test_goods_bill_limited_to_received_quantity(self):
        order = self._make_order(self.goods, 10)
        self._receive(order, 6)
        line = order.order_line
        self.assertEqual(line.qty_received, 6.0)
        self.assertEqual(line.qty_to_invoice, 6.0)
        self.assertEqual(order.invoice_status, "to invoice")

        order.action_create_invoice()
        self.assertEqual(order.invoice_status, "invoiced")
        self.assertEqual(len(order.invoice_ids), 1)
        self.assertEqual(order.invoice_ids.invoice_line_ids.quantity, 6.0)
        self.assertEqual(line.qty_to_invoice, 0.0)
        # ของที่ยังไม่รับ (4) ยังออกบิลไม่ได้
        self.assertEqual(line.qty_received, 6.0)

    def test_remaining_goods_billable_after_receipt(self):
        order = self._make_order(self.goods, 10)
        self._receive(order, 6)
        order.action_create_invoice()

        self._receive(order, 4)
        line = order.order_line
        self.assertEqual(line.qty_received, 10.0)
        self.assertEqual(line.qty_to_invoice, 4.0)

        order.action_create_invoice()
        self.assertEqual(line.qty_invoiced, 10.0)
        self.assertEqual(line.qty_to_invoice, 0.0)
        self.assertEqual(order.invoice_status, "invoiced")

    # ------------------------------------------------------------------
    # 2-way match: งานบริการ (ต้องไม่ถูกกระทบ)
    # ------------------------------------------------------------------
    def test_service_bill_not_blocked_by_receipt(self):
        order = self._make_order(self.service, 10)
        line = order.order_line
        self.assertEqual(line.qty_received, 0.0)
        self.assertEqual(line.qty_to_invoice, 10.0)
        self.assertEqual(order.invoice_status, "to invoice")

        order.action_create_invoice()
        self.assertEqual(len(order.invoice_ids), 1)
        self.assertEqual(order.invoice_ids.invoice_line_ids.quantity, 10.0)
        self.assertEqual(line.qty_to_invoice, 0.0)
        self.assertEqual(order.invoice_status, "invoiced")
