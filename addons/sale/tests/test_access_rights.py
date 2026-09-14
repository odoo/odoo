from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestAccessRights(SaleCommon, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = cls._create_new_portal_user()
        cls.user_internal = cls._create_new_internal_user()

        cls.sale_user2 = cls.env["res.users"].create(
            {
                "name": "salesman_2",
                "login": "salesman_2",
                "email": "default_user_salesman_2@example.com",
                "signature": "--\nMark",
                "notification_type": "email",
                "group_ids": [(6, 0, cls.group_sale_salesman.ids)],
            }
        )

        cls.sale_order.user_id = cls.sale_user

    def test_access_sales_manager(self):
        SaleOrder = self.env["sale.order"].with_user(self.sale_manager)
        so_as_sale_manager = SaleOrder.browse(self.sale_order.id)

        so_as_sale_manager.read()
        so_as_sale_manager.write({"user_id": self.sale_user2.id})

        sale_order = SaleOrder.create(
            {
                "partner_id": self.partner.id,
                "user_id": self.sale_user.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                        }
                    )
                ],
            }
        )
        self.assertIn(
            sale_order.id,
            SaleOrder.search([]).ids,
            "Sales manager should be able to create the SO of other salesperson",
        )
        sale_order.action_confirm()
        with self.assertRaises(UserError), mute_logger("odoo.models.unlink"):
            sale_order.unlink()

        so_as_sale_manager.unlink()
        self.assertNotIn(
            so_as_sale_manager.id,
            SaleOrder.search([]).ids,
            "Sales manager should be able to delete the SO",
        )

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule")
    def test_access_sales_person(self):
        SaleOrder = self.env["sale.order"].with_user(self.sale_user2)
        so_as_salesperson = SaleOrder.browse(self.sale_order.id)

        with self.assertRaises(AccessError):
            so_as_salesperson.read()

        self.sale_order.write({"user_id": self.sale_user2.id})

        so_as_salesperson.read()
        so_as_salesperson.write({"client_order_ref": "Salesperson reference"})

        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(self.sale_user2).create(
                {"partner_id": self.partner.id, "user_id": self.sale_user.id}
            )

        with self.assertRaises(AccessError):
            so_as_salesperson.unlink()

        so_as_salesperson.action_confirm()

        move_as_salesperson = so_as_salesperson._create_invoices().with_user(
            self.sale_user2
        )
        with self.assertRaises(AccessError):
            move_as_salesperson.action_post()

        move_as_salesperson.sudo().action_post()

        composer = (
            self.env["account.move.send.wizard"]
            .with_user(self.sale_user2)
            .with_context(
                active_model="account.move", active_ids=move_as_salesperson.ids
            )
            .create({})
        )

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer.action_send_and_print()

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule")
    def test_access_portal_user(self):
        SaleOrder = self.env["sale.order"].with_user(self.user_portal)
        so_as_portal_user = SaleOrder.browse(self.sale_order.id)

        with self.assertRaises(AccessError):
            so_as_portal_user.read()

        self.sale_order.partner_id = self.user_portal.partner_id
        self.sale_order.action_confirm()
        with self.assertRaises(AccessError):
            so_as_portal_user.write({"client_order_ref": "Portal reference"})
        with self.assertRaises(AccessError):
            SaleOrder.create(
                {
                    "partner_id": self.partner.id,
                }
            )
        self.sale_order.action_cancel()
        with self.assertRaises(AccessError):
            so_as_portal_user.unlink()

    @mute_logger("odoo.addons.base.models.ir_model")
    def test_access_employee(self):
        SaleOrder = self.env["sale.order"].with_user(self.user_internal)
        so_as_internal_user = SaleOrder.browse(self.sale_order.id)

        with self.assertRaises(AccessError):
            so_as_internal_user.read()
        with self.assertRaises(AccessError):
            so_as_internal_user.write({"client_order_ref": "Employee reference"})
        with self.assertRaises(AccessError):
            SaleOrder.create(
                {
                    "partner_id": self.partner.id,
                }
            )
        with self.assertRaises(AccessError):
            so_as_internal_user.unlink()
