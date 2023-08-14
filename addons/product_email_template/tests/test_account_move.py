# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestAccountMove(AccountTestInvoicingCommon):
    def setUp(self):
        super().setUp()
        Template = self.env['mail.template']
        self.template = Template.create({
            'name': 'Product Template',
            'subject': 'YOUR PRODUCT',
            'model_id': self.env['ir.model']._get_id('product.template')
        })
        self.customer = self.env['res.partner'].create({
            'name': 'James Bond',
            'email': 'james.bond@yopmail.com'
        })
        self.product_a.email_template_id = self.template.id

    def test_send_product_template_email_on_invoice_post(self):
        id_max = self.env['mail.message'].search([], order='id desc', limit=1)
        if id_max:
            id_max = id_max[0].id
        else:
            id_max = 0
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Walter PPK',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            })]
        })
        invoice.action_post()
        message_sent = self.env['mail.message'].search([('id', '>', id_max), ('subject', '=', 'YOUR PRODUCT')])
        self.assertEqual(len(message_sent), 1, 'Should send 1 message for product')
        self.assertTrue(message_sent[0].email_from, 'Should have from email address')

    def test_send_as_system_when_sudo(self):
        """
        Test scenario of a product ordered through the portal.
        """
        id_max = self.env['mail.message'].search([], order='id desc', limit=1)
        if id_max:
            id_max = id_max[0].id
        else:
            id_max = 0
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Walter PPK',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            })]
        })
        pub_user = self.env['res.users'].create({
            'login': 'test_public_user',
            'name': 'test_public_user',
            'email': False,
            'groups_id': [(6, 0, [self.env.ref('base.group_public').id])]
        })
        invoice.with_user(pub_user).sudo().action_post()
        message_sent = self.env['mail.message'].search([('id', '>', id_max), ('subject', '=', 'YOUR PRODUCT')])
        self.assertEqual(len(message_sent), 1, 'Should send 1 message for product')
        self.assertTrue(message_sent[0].email_from, 'Should have from email address')
