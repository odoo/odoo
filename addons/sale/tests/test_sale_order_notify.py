from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.sale.tests.common import SaleCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install', 'mail_flow')
class TestSaleOrderNotify(MailCommon, SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.salesperson = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Marc Demo',
            'login': 'marc_demo_notify',
            'email': 'marc.demo@test.example.com',
            'notification_type': 'email',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
            ])],
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'OpenWood',
            'email': 'openwood@test.example.com',
        })
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'user_id': cls.salesperson.id,
            'order_line': [(0, 0, {'product_id': cls.product.id, 'product_uom_qty': 1})],
        })
        cls.order.message_subscribe(partner_ids=(cls.customer | cls.salesperson.partner_id).ids)
        cls.order.action_confirm()
        cls.flush_tracking_queue() if hasattr(cls, 'flush_tracking_queue') else None

    def _post_as_admin(self, **kwargs):
        with self.mock_mail_gateway(mail_unlink_sent=False):
            message = self.order.with_user(self.user_admin).message_post(
                body='Hello from the admin',
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                **kwargs,
            )
        return message

    def test_chatter_comment_single_email_customer_to_salesperson_cc(self):
        """ One email: customer in To, salesperson in Cc. No second email
        addressed to the salesperson with the customer in To. """
        self._post_as_admin()

        customer_mails = [
            m for m in self._mails
            if self.customer.email in ' '.join(m['email_to'])
        ]
        self.assertEqual(
            len(customer_mails), 1,
            "The customer must appear on exactly one email for the message")
        mail = customer_mails[0]
        self.assertEqual(len(self._mails), 1, "Only one email should be sent")
        self.assertIn(self.customer.email, ' '.join(mail['email_to']))
        self.assertNotIn(self.salesperson.email, ' '.join(mail['email_to']))
        self.assertIn(self.salesperson.email, ' '.join(mail['email_cc']))