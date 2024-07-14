# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import http
from odoo.exceptions import ValidationError
from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class HelpDeskPortal(HttpCase):

    def setUp(self):
        super(HelpDeskPortal, self).setUp()
        self.team_with_sla = self.env['helpdesk.team'].create({
            'name': 'Team with SLAs',
            'use_sla': True,
            'use_website_helpdesk_form': True,
            'is_published': True,
        })
        self.stage_new = self.env['helpdesk.stage'].create({
            'name': 'New',
            'sequence': 10,
            'team_ids': [(4, self.team_with_sla.id, 0)],
        })
        self.sla = self.env['helpdesk.sla'].create({
            'name': "2 days to be in progress",
            'stage_id': self.stage_new.id,
            'time': 16,
            'team_id': self.team_with_sla.id,
        })

    def test_portal_ticket_submission(self):
        """ Public user should be able to submit a ticket"""
        self.authenticate(None, None)
        ticket_data = {
            'name': "Broken product",
            'partner_name': 'Jean Michel',
            'partner_email': 'jean@michel.com',
            'team_id': self.team_with_sla.id,
            'description': 'Your product is broken',
            'csrf_token': http.Request.csrf_token(self),
        }
        files = [('file', ('test.txt', b'test', 'plain/text'))]
        response = self.url_open('/website/form/helpdesk.ticket', data=ticket_data, files=files)
        ticket = self.env['helpdesk.ticket'].browse(response.json().get('id'))
        self.assertTrue(ticket.exists())
        ticket_submitted_response = self.url_open('/your-ticket-has-been-submitted')
        self.assertEqual(ticket_submitted_response.status_code, 200)
        ticket_submitted_response_ticket_id = (
            re.search(
                rb'Your Ticket Number is #<span>(?P<ticket_id>.*?)</span>',
                ticket_submitted_response.content)
            .group('ticket_id')
        ).decode()
        self.assertIn(
            ticket_submitted_response_ticket_id,
            (ticket.ticket_ref, str(ticket.id)),
            "Ticket ID on the submitted page does not match with the ticket created"
        )

    def test_portal_ticket_submission_multiple(self):
        REPEAT = 3
        for i in range(REPEAT):
            try:
                self.test_portal_ticket_submission()
            except AssertionError:
                raise AssertionError("Fail on the iteration %s/%s" % (i+1, REPEAT))

    def test_portal_configure_team(self):
        """ Configure the team while the visibility is internal and public"""
        self.team_with_sla.use_website_helpdesk_form = False

        with self.assertRaises(ValidationError):
            self.team_with_sla.write({
                'privacy_visibility': 'internal',
                'use_website_helpdesk_form': True
            })

        self.team_with_sla.write({
            'privacy_visibility': 'portal',
            'use_website_helpdesk_form': True
        })
        self.assertTrue(self.team_with_sla)
