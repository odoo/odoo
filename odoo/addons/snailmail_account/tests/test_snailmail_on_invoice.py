# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase, tagged
from odoo import Command

@tagged('post_install', '-at_install')
class TestSnailmailOnInvoice(TransactionCase):
    def test_snailmail_on_invoice_for_partner_without_email(self):
        """"
        Checks that a snailmail letter is created when one print and send by post a customer invoice
        for a partner without email.
        """

        partner_without_email = self.env['res.partner'].create({
            'name': 'Partner_without_email',
            'email': False,
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'sale_ok': True,
            'standard_price': 100.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_without_email.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [Command.create({'product_id': product.id})],
        })
        invoice.action_post()

        print_wiz = self.env['account.move.send'].create({
            'move_ids': invoice.ids,
            'checkbox_download': False,
            'checkbox_send_mail': False,
            'checkbox_send_by_post': True,
        })
        print_wiz.action_send_and_print()

        letter = self.env['snailmail.letter'].search([
            ('partner_id', '=', partner_without_email.id),
            ('model', '=', invoice._name),
            ('res_id', '=', invoice.id),
        ], limit=1)
        self.assertTrue(letter)
