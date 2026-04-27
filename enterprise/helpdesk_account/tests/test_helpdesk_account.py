# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests import common
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestHelpdeskAccount(common.HelpdeskCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # give the test team ability to create credit note
        cls.test_team.use_credit_notes = True
        # create a sale order and invoice
        cls.product = cls.env['product.product'].create({
            'name': 'product 1',
            'type': 'consu',
            'invoice_policy': 'order',
        })
        cls.so = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })

    def test_helpdesk_account_1(self):
        """ Test used to check that the functionalities of After sale in Helpdesk (credit note).
        """
        self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'price_unit': 10,
            'order_id': self.so.id,
        })
        self.so.action_confirm()
        self.so._create_invoices()
        invoice = self.so.invoice_ids
        invoice.action_post()
        # helpdesk.ticket access rights
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': self.partner.id,
            'team_id': self.test_team.id,
            'sale_order_id': self.so.id,
        })

        credit_note_form = Form(self.env['account.move.reversal'].with_context({
            'default_helpdesk_ticket_id': ticket.id,
        }), view=self.env.ref('helpdesk_account.view_account_move_reversal_inherit_helpdesk_account'))
        for inv in self.so.invoice_ids:
            credit_note_form.move_ids.add(inv)
        credit_note_form.reason = 'test'
        credit_note = credit_note_form.save()
        res = credit_note.refund_moves()
        refund = self.env['account.move'].browse(res['res_id'])

        self.assertEqual(len(refund), 1, "No refund created")
        self.assertEqual(refund.state, 'draft', "Wrong status of the refund")
        self.assertEqual(refund.ref, 'Reversal of: %s, %s' % (invoice.name, credit_note_form.reason), "The reference is wrong")
        self.assertEqual(len(ticket.invoice_ids), 1,
            "The ticket should be linked to a credit note")
        self.assertEqual(ticket.invoices_count, 1,
            "The ticket should be linked to a credit note")
        self.assertEqual(refund[0].id, ticket.invoice_ids[0].id,
            "The correct credit note should be referenced in the ticket")

        refund.action_post()
        last_message = str(ticket.message_ids[0].body)

        self.assertTrue(refund.display_name in last_message and 'Refund' in last_message,
            'Refund Post should be logged on the ticket')

    def test_create_multiple_credit_notes_in_ticket(self):
        """ Test used to check a multiple credit notes are created in the ticket.

        Test Case:
        ----------
            - Create sale order With 10 product Qty
            - Confirm sale order and create invoice
            - Confirm Invoice
            - Create helpdesk Ticket
            - Create a credit note(Partial Refund)
            - Confirm a credit note
            - Create a credit note(Full Refund)
            - Check the credit note state
            - Create a credit note With Form
        """
        journal_id = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.main_company_id)], limit=1).id
        self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'price_unit': 10,
            'order_id': self.so.id,
        })
        self.so.action_confirm()
        self.so._create_invoices()
        invoice = self.so.invoice_ids
        invoice.action_post()
        # helpdesk.ticket access rights
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': self.partner.id,
            'team_id': self.test_team.id,
            'sale_order_id': self.so.id,
        })

        # create a Partial Refund
        credit_note = self.env['account.move.reversal'].create({
            'helpdesk_ticket_id': ticket.id,
            'reason': 'test',
            'journal_id': journal_id,
            'move_ids': self.so.invoice_ids,
        })
        res = credit_note.refund_moves()
        move = self.env['account.move'].browse(res['res_id'])
        move.invoice_line_ids.quantity = 2
        move.action_post()
        self.assertEqual(invoice.state, 'posted', "credit note should be posted.")
        #  create a Full Refund
        credit_note = self.env['account.move.reversal'].create({
            'helpdesk_ticket_id': ticket.id,
            'reason': 'test',
            'journal_id': journal_id,
            'move_ids': invoice,
        })
        res = credit_note.modify_moves()
        new_invoice = self.env['account.move'].browse(res['res_id'])
        self.assertEqual(invoice.state, 'posted', "reversed invoice remain in posted state")
        self.assertEqual(new_invoice.state, 'draft', "newly created invoice should be in draft state.")

        # create a Refund
        credit_note_form = Form(self.env['account.move.reversal'].with_context({
            'default_helpdesk_ticket_id': ticket.id,
        }), view=self.env.ref('helpdesk_account.view_account_move_reversal_inherit_helpdesk_account'))
        for inv in self.so.invoice_ids:
            credit_note_form.move_ids.add(inv)
        credit_note_form.reason = 'test'
        credit_note_form.save()
