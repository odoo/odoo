from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


class TestWebsiteEventSale(HttpCaseWithUserPortal, TestWebsiteEventSaleCommon):

    def test_website_event_sale(self):
        """ Test saleorder is created for tickets having price only """
        self.authenticate('portal', 'portal')
        free_ticket = self.env['event.event.ticket'].create({
            'event_id': self.event.id,
            'name': 'Free',
            'product_id': self.product_event.id,
            'price': 0,
        })
        event_questions = self.event.question_ids
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        phone_question = event_questions.filtered(lambda q: q.question_type == 'phone')
        self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': free_ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertFalse(self.env['sale.order'].search([
            ('partner_id', '=', self.partner_portal.id),
            ('order_line.event_ticket_id', '=', free_ticket.id)
        ]), "Sale order should not be created for the free tickets")
        self.assertEqual(len(self.event.registration_ids), 1)

        self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': self.ticket.id,
            f'2-name-{name_question.id}': 'joe',
            f'2-email-{email_question.id}': 'joe@test.lan',
            f'2-phone-{phone_question.id}': '8989898988',
            '2-event_ticket_id': free_ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })

        self.assertEqual(len(self.event.registration_ids), 3)
        self.assertFalse(self.env['sale.order'].search([
            ('partner_id', '=', self.partner_portal.id),
            ('order_line.event_ticket_id', '=', free_ticket.id)
        ]), "Sale order should not be created for the free tickets")
        self.assertTrue(self.env['sale.order'].search([
            ('partner_id', '=', self.partner_portal.id),
            ('order_line.event_ticket_id', '=', self.ticket.id)
        ]), "Sale order should be created for the paid tickets")
