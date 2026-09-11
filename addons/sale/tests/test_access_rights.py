# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestAccessRights(SaleCommon, MailCommon):
    _test_user_groups = (
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = cls._create_new_portal_user()
        cls.user_internal = cls._create_new_internal_user()

        cls.sale_user2 = cls.env["res.users"].sudo().create({
            "name": "salesman_2",
            "login": "salesman_2",
            "email": "default_user_salesman_2@example.com",
            "signature": "--\nMark",
            "notification_type": "email",
            "group_ids": [(6, 0, cls.group_sale_salesman.ids)],
        })

        # Create the SO with a specific salesperson
        cls.sale_order.user_id = cls.sale_user

    def test_access_sales_manager(self):
        """Test sales manager's access rights."""
        SaleOrder = self.env["sale.order"].with_user(self.sale_manager)
        so_as_sale_manager = SaleOrder.browse(self.sale_order.id)

        # Manager can see the SO which is assigned to another salesperson
        so_as_sale_manager.read()
        # Manager can change a salesperson of the SO
        so_as_sale_manager.write({"user_id": self.sale_user2.id})

        # Manager can create the SO for other salesperson
        sale_order = SaleOrder.create({"partner_id": self.partner.id, "user_id": self.sale_user.id})
        self.assertIn(
            sale_order.id,
            SaleOrder.search([]).ids,
            "Sales manager should be able to create the SO of other salesperson",
        )
        # Manager can confirm the SO
        sale_order.action_confirm()
        # Manager can not delete confirmed SO
        with self.assertRaises(UserError), mute_logger("odoo.models.unlink"):
            sale_order.unlink()

        # Manager can delete the SO of other salesperson if SO is in 'draft' or 'cancel' state
        so_as_sale_manager.unlink()
        self.assertNotIn(
            so_as_sale_manager.id,
            SaleOrder.search([]).ids,
            "Sales manager should be able to delete the SO",
        )

    @mute_logger('odoo.addons.base.models.ir_access')
    def test_access_sales_person(self):
        """Test Salesperson's access rights."""
        SaleOrder = self.env["sale.order"].with_user(self.sale_user2)
        so_as_salesperson = SaleOrder.browse(self.sale_order.id)

        # Salesperson can see only their own sales order
        with self.assertRaises(AccessError):
            so_as_salesperson.read()

        # Now assign the SO to themselves
        # (using self.sale_order to do the change as superuser)
        self.sale_order.write({"user_id": self.sale_user2.id})

        # The salesperson is now able to read it
        so_as_salesperson.read()
        # Salesperson can change a Sales Team of SO
        so_as_salesperson.write({"team_id": self.sale_team.id})

        # Salesperson can't create a SO for other salesperson
        with self.assertRaises(AccessError):
            self.env["sale.order"].with_user(self.sale_user2).create({
                "partner_id": self.partner.id,
                "user_id": self.sale_user.id,
            })

        # Salesperson can't delete Sale Orders
        with self.assertRaises(AccessError):
            so_as_salesperson.unlink()

        # Salesperson can confirm the SO
        so_as_salesperson.action_confirm()

        # Salesperson can't confirm the related move
        move_as_salesperson = so_as_salesperson._create_invoices().with_user(self.sale_user2)
        with self.assertRaises(AccessError):
            move_as_salesperson.action_post()

        move_as_salesperson.sudo().action_post()

        composer = (
            self
            .env["account.move.send.wizard"]
            .with_user(self.sale_user2)
            .with_context(active_model="account.move", active_ids=move_as_salesperson.ids)
            .create({})
        )

        # Salesperson can send & print
        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer.action_send_and_print()

    @mute_logger('odoo.addons.base.models.ir_access')
    def test_access_bank_account_on_account_move(self):
        """A salesperson can read the recipient bank account shown on an
        account.move they can read (res.partner.bank document rule)."""

        company_bank = self.env["res.partner.bank"].sudo().create({
            "account_number": "SP-COMP-0001",
            "partner_id": self.env.company.partner_id.id,
            "allow_out_payment": True,  # trusted, so posting an inbound invoice doesn't block
        })
        customer_bank = self.env["res.partner.bank"].sudo().create({
            "account_number": "SP-CUST-0001",
            "partner_id": self.partner.id,
        })

        # Real flow (done as superuser): SO owned by the salesperson -> invoice
        # -> post -> reverse. Both partner_bank_id values are set by the real
        # computes / reversal wizard; we never hand-set them.
        sale_order = self.sale_order.sudo()
        sale_order.user_id = self.sale_user2
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.invoice_user_id = self.sale_user2
        invoice.action_post()

        # On an out_invoice the recipient is the company, so partner_bank_id
        # computed to the *company* bank, which the salesperson can read.
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.partner_bank_id, company_bank)
        self.assertEqual(invoice.partner_bank_id.partner_id, self.env.company.partner_id)
        self.env.invalidate_all()
        invoice.partner_bank_id.with_user(self.sale_user2).read(["account_number"])

        reversal = self.env["account.move.reversal"].sudo().with_context(
            active_model="account.move", active_ids=invoice.ids,
        ).create({"journal_id": invoice.journal_id.id})
        reversal.reverse_moves()
        credit_note = reversal.new_move_ids
        credit_note.ensure_one()

        # On an out_refund the recipient is the customer, so partner_bank_id
        # computed to the *customer* bank.
        self.assertEqual(credit_note.move_type, "out_refund")
        self.assertEqual(credit_note.invoice_user_id, self.sale_user2)
        self.assertEqual(credit_note.partner_bank_id, customer_bank)

        # The salesperson can read the credit note and, through it, the bank.
        self.env.invalidate_all()
        credit_note.with_user(self.sale_user2).read(["name"])
        customer_bank.with_user(self.sale_user2).read(["account_number"])

        # An unrelated customer's bank (on no move the salesperson can read)
        # stays out of reach.
        other_bank = self.env["res.partner.bank"].sudo().create({
            "account_number": "SP-OTHER-0001",
            "partner_id": self.env["res.partner"].sudo().create({
                "name": "Unrelated customer",
            }).id,
        })
        with self.assertRaises(AccessError):
            other_bank.with_user(self.sale_user2).read(["account_number"])

    @mute_logger('odoo.addons.base.models.ir_access')
    def test_access_portal_user(self):
        """Test portal user's access rights."""
        SaleOrder = self.env["sale.order"].with_user(self.user_portal)
        so_as_portal_user = SaleOrder.browse(self.sale_order.id)

        # Portal user can see the confirmed SO for which they are assigned as a customer
        with self.assertRaises(AccessError):
            so_as_portal_user.read()

        self.sale_order.partner_id = self.user_portal.partner_id
        self.sale_order.action_confirm()
        # Portal user can't edit the SO
        with self.assertRaises(AccessError):
            so_as_portal_user.write({"team_id": self.sale_team.id})
        # Portal user can't create the SO
        with self.assertRaises(AccessError):
            SaleOrder.create({"partner_id": self.partner.id})
        # Portal user can't delete the SO which is in 'draft' or 'cancel' state
        self.sale_order.action_cancel()
        with self.assertRaises(AccessError):
            so_as_portal_user.unlink()

    @mute_logger('odoo.addons.base.models.ir_access')
    def test_access_employee(self):
        """Test classic employee's access rights."""
        SaleOrder = self.env["sale.order"].with_user(self.user_internal)
        so_as_internal_user = SaleOrder.browse(self.sale_order.id)

        # Employee can't see any SO
        with self.assertRaises(AccessError):
            so_as_internal_user.read()
        # Employee can't edit the SO
        with self.assertRaises(AccessError):
            so_as_internal_user.write({"team_id": self.sale_team.id})
        # Employee can't create the SO
        with self.assertRaises(AccessError):
            SaleOrder.create({"partner_id": self.partner.id})
        # Employee can't delete the SO
        with self.assertRaises(AccessError):
            so_as_internal_user.unlink()

    def test_demo_user_creates_sale_order_with_tracked_product(self):
        """Verify user with product view access can create sales order with tracked product."""
        self.product.is_storable = True
        sale_order = (
            self
            .env["sale.order"]
            .with_user(self.sale_user2)
            .create({
                "partner_id": self.partner.id,
                "order_line": [Command.create({"product_id": self.product.id})],
            })
        )
        sale_order.action_confirm()
        self.assertTrue(sale_order.state == "sale")

    def test_access_invoice_from_sale_order(self):
        """ Test access rights on invoices created from sale orders when the current user has no
        accounting access rights but is the default salesperson related to the created invoice.

        Cash rounding can trigger access checks on accounting records; this test ensures
        the salesperson retains read/write access via the default user_id relation.
        """
        # Enable cash rounding in the settings, create one and set it as default for invoices
        admin_user = self.env.ref('base.user_admin')
        self.env.user.group_ids += self.env.ref('account.group_cash_rounding')
        rounding = self.env['account.cash.rounding'].with_user(admin_user).create({
            'name': 'rounding',
        })
        self.env['ir.default'].with_user(admin_user).set('account.move', 'invoice_cash_rounding_id', rounding.id)
        # Create a sale order as a salesperson that has no accounting access rights
        sale_order = self.env['sale.order'].with_user(self.sale_user).create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                }),
            ],
        })
        # Salesperson confirms the SO and creates the related invoice
        sale_order.action_confirm()
        invoice = sale_order._create_invoices().with_user(self.sale_user)
        # Ensure cache is clear so that the user needs to access fields
        rounding.invalidate_recordset(["strategy"])
        # Ensure the salesperson can access the invoice even when a cash rounding is set
        with Form(invoice) as form:
            self.assertEqual(form.user_id, self.sale_user)
