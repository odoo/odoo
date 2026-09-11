import odoo

from odoo import Command
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPosBankAccess(CommonPosTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_user = cls.env['res.users'].create({
            'name': 'Pure POS user',
            'login': 'pure_pos_user',
            'group_ids': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('point_of_sale.group_pos_user').id,
            ])],
        })
        cls.customer_bank = cls._trusted_bank(cls, cls.partner_adgu, 'CUST-POS-1')
        cls.company_bank = cls._trusted_bank(cls, cls.company.partner_id, 'COMP-POS-1')

    def _trusted_bank(self, partner, number):
        return self.env['res.partner.bank'].sudo().create({
            'account_number': number,
            'partner_id': partner.id,
            'allow_out_payment': True,
        })

    def test_get_partner_bank_id_refund_customer_bank(self):
        """Case 1 (refund → customer bank) NEEDS the residual sudo: a pure POS
        user cannot read an arbitrary customer's bank and has no move to lean on,
        so without elevation the o2m read drops the refund's recipient bank."""
        self.pos_config_usd.open_ui()
        self.partner_adgu.write({'bank_ids': [Command.link(self.customer_bank.id)]})
        _order, refund = self.create_backend_pos_order({
            'line_data': [{'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}],
            'order_data': {'partner_id': self.partner_adgu.id},
            'payment_data': [{'payment_method_id': self.bank_payment_method.id}],
            'refund_data': [{'payment_method_id': self.bank_payment_method.id}],
        })
        refund.write({'partner_id': self.partner_adgu.id})
        bank_id = refund.with_user(self.pos_user)._get_partner_bank_id()
        self.assertEqual(bank_id, self.customer_bank.id,
                         "Pure POS user should resolve the customer bank on a refund")

    def test_get_mail_attachments_invoice_render(self):
        """The 'Send Receipt' email renders the customer invoice PDF. Needs no
        sudo: point_of_sale.group_pos_user already has an account.move read rule
        for POS-linked invoices, and the recipient bank on it is the company
        bank (company rule)."""
        self.pos_config_usd.open_ui()
        order, _refund = self.create_backend_pos_order({
            'line_data': [{'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}],
            'order_data': {'partner_id': self.partner_adgu.id, 'to_invoice': True},
            'payment_data': [{'payment_method_id': self.bank_payment_method.id}],
        })
        self.assertTrue(order.account_move, "order should be invoiced")
        attachments = order.with_user(self.pos_user)._get_mail_attachments(
            order.name, False, False)
        self.assertTrue(attachments, "invoice PDF attachment should be produced")
