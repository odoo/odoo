from freezegun import freeze_time

from odoo import SUPERUSER_ID
from odoo.tests import tagged
from odoo.addons.stock.tests.common import TestStockCommon
from odoo import fields


@tagged("post_install", "-at_install")
class TestStockOrderpointActivity(TestStockCommon):
    def test_orderpoint_activity_portal_context_leak(self):

        company_b = self.env["res.company"].search([("id", "!=", self.env.company.id)], limit=1)
        if not company_b:
            self.env.user.lang = "en_US"
            company_b = self.env["res.company"].create({"name": "Thanks to Nature Test"})

        warehouse_b = self.env["stock.warehouse"].search([("company_id", "=", company_b.id)], limit=1)
        if not warehouse_b:
            warehouse_b = self.env["stock.warehouse"].create(
                {
                    "name": "Website WH",
                    "code": "WWH",
                    "company_id": company_b.id,
                }
            )

        shared_product = self.env["product.product"].create(
            {
                "name": "Shared Product",
                "type": "consu",
                "is_storable": True,
                "company_id": False,
            }
        )

        portal_user = self.env["res.users"].create(
            {
                "name": "Portal Customer",
                "login": "portal_customer_nature_leak_test",
                "email": "customer@naturetest.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
            }
        )

        # Ensure procurement is guaranteed to fail by deactivating matching stock rules
        self.env["stock.rule"].search(
            [("location_dest_id", "=", warehouse_b.lot_stock_id.id)]
        ).write({"active": False})

        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "Failing Routing Rule",
                "product_id": shared_product.id,
                "warehouse_id": warehouse_b.id,
                "location_id": warehouse_b.lot_stock_id.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
                "trigger": "auto",
                "company_id": company_b.id,
            }
        )

        orderpoint.write(
            {
                "product_min_qty": 10.0,
                "product_max_qty": 10.0,
            }
        )

        orderpoint.with_user(portal_user).sudo()._procure_orderpoint_confirm(
            company_id=company_b.id, raise_user_error=False
        )

        activity = self.env["mail.activity"].search(
            [
                ("res_model", "in", ["product.template", "product.product"]),
                (
                    "res_id",
                    "in",
                    [shared_product.product_tmpl_id.id, shared_product.id],
                ),
                (
                    "activity_type_id",
                    "=",
                    self.env.ref("mail.mail_activity_data_warning").id,
                ),
            ],
            limit=1,
        )

        self.assertTrue(
            activity,
            "An exception activity should have been created on the product template.",
        )

        self.assertEqual(
            activity.create_uid.id,
            SUPERUSER_ID,
            "The activity creator leaked! It must be created by OdooBot (ID 1), not the portal user.",
        )

    def test_orderpoint_deadline_timezone(self):
        """
        Tests that the lead_horizon_date is on the same day even with a timezone
        that is different from UTC
        """
        self.env.company.tz = 'Australia/Sydney'
        self.env.company.horizon_days = 0
        self.productA.is_storable = True
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': 'Sydney RR',
            'product_id': self.productA.id,
            'product_min_qty': 0,
            'product_max_qty': 10,
        })

        with freeze_time('2026-11-03 14:00:00'):
            orderpoint.invalidate_recordset(['lead_horizon_date', 'lead_days'])
            self.assertEqual(orderpoint.lead_horizon_date, fields.Date.from_string('2026-11-04'))
            deadline = orderpoint._get_orderpoint_procurement_date()
            self.assertEqual(deadline, fields.Datetime.from_string('2026-11-04 01:00:00'))
