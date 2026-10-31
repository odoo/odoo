# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestAccumulatedSales(TestPointOfSaleHttpCommon):

    def test_accumulated_total_sales_updates_when_order_is_paid(self):
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        session = self.main_pos_config.current_session_id
        order = self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.main_pos_config.id,
                "session_id": session.id,
                "partner_id": self.partner_a.id,
                "lines": [
                    Command.create(
                        {
                            "name": self.product_a.display_name,
                            "product_id": self.product_a.id,
                            "price_unit": 100,
                            "discount": 0,
                            "qty": 1,
                            "tax_ids": [Command.clear()],
                            "price_subtotal": 100,
                            "price_subtotal_incl": 100,
                        },
                    ),
                ],
                "pricelist_id": self.main_pos_config.pricelist_id.id,
                "amount_paid": 100.0,
                "amount_total": 100.0,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "to_invoice": False,
            },
        )

        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 0.0)
        order.action_pos_order_paid()
        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 100.0)
        order.action_pos_order_paid()
        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 100.0)

    def test_l10n_ph_fields_are_not_copied_when_duplicating_pos_config(self):
        self.main_pos_config.write({
            "l10n_ph_accumulated_total_sales": 500.0,
            "l10n_ph_machine_identification_number": "MIN-0001",
            "l10n_ph_machine_serial_number": "SER-0001",
        })

        copied_config = self.main_pos_config.copy()

        self.assertRecordValues(copied_config, [{
            "l10n_ph_accumulated_total_sales": 0.0,
            "l10n_ph_machine_identification_number": False,
            "l10n_ph_machine_serial_number": False,
        }])

    def test_accumulated_total_sales_updates_when_order_is_synced_from_ui(self):
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        session = self.main_pos_config.current_session_id

        ui_order = {
            "amount_paid": 100.0,
            "amount_return": 0.0,
            "amount_tax": 0.0,
            "amount_total": 100.0,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "pricelist_id": self.main_pos_config.pricelist_id.id,
            "name": "Order 98765-123-0001",
            "lines": [
                (
                    0,
                    0,
                    {
                        "id": 42,
                        "name": self.product_a.display_name,
                        "product_id": self.product_a.id,
                        "price_unit": 100.0,
                        "discount": 0.0,
                        "qty": 1,
                        "tax_ids": [[6, False, []]],
                        "price_subtotal": 100.0,
                        "price_subtotal_incl": 100.0,
                    },
                ),
            ],
            "session_id": session.id,
            "payment_ids": [
                (
                    0,
                    0,
                    {
                        "amount": 100.0,
                        "name": fields.Datetime.now(),
                        "payment_method_id": session.payment_method_ids[:1].id,
                    },
                ),
            ],
            "uuid": "98765-123-0001",
            "user_id": self.env.uid,
            "to_invoice": False,
        }

        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 0.0)
        self.env["pos.order"].sync_from_ui([ui_order])
        synced_order = self.env["pos.order"].search(
            [("uuid", "=", "98765-123-0001")],
            limit=1,
        )
        self.assertRecordValues(synced_order, [{
            "state": "paid",
            "l10n_ph_accumulated_counted": True,
            "config_id": self.main_pos_config.id,
        }])
        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 100.0)
