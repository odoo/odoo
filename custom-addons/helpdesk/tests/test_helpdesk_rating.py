# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from .common import HelpdeskCommon
from odoo.tests.common import HttpCase
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestHelpdeskRating(HelpdeskCommon, HttpCase, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })
        cls.partner_1_user = mail_new_test_user(
            cls.env,
            name=cls.partner_1.name,
            login='partner_1',
            email=cls.partner_1.email,
            groups='base.group_portal',
        )

        # Enable rating feature
        cls.test_team.write({'use_rating': True})

        HelpdeskTicket = cls.env['helpdesk.ticket'].with_context({'mail_create_nolog': True})
        cls.test_team_ticket1 = HelpdeskTicket.create({
            'name': 'Ticket 1',
            'team_id': cls.test_team.id,
            'user_id': cls.helpdesk_manager.id,
        })
        cls.test_team_ticket2 = HelpdeskTicket.create({
            'name': 'Ticket 2',
            'team_id': cls.test_team.id,
            'user_id': cls.helpdesk_user.id,
        })

        cls.default_rating_vals = {
            'res_model_id': cls.env['ir.model']._get('helpdesk.ticket').id,
            'parent_res_model_id': cls.env['ir.model']._get('helpdesk.team').id,
            'parent_res_id': cls.test_team.id,
            'partner_id': cls.partner_1.id,
            'consumed': True,
        }

    def test_rating_notification(self):
        self.env['rating.rating'].create({
            **self.default_rating_vals,
            'rated_partner_id': self.helpdesk_user.partner_id.id,
            'res_id': self.test_team_ticket2.id,
            'consumed': False,
            'access_token': 'HELP_TEST',
        })

        rating = 5
        feedback = 'Great!'

        self.test_team_ticket2.rating_apply(rating, token='HELP_TEST', feedback=feedback)
        message = self.test_team_ticket2.message_ids

        self.assertEqual(len(message), 1, 'A message should have been posted in the chatter.')
        self.assertEqual(message.author_id, self.partner_1, 'The message should be posted by the rating partner.')
        self.assertIn(f"{rating}/5", message.body, f"The posted rating should be {rating}/5.")
        self.assertIn(feedback, message.body, 'The posted rating should contain the customer feedback.')

    def test_rating_website(self):
        self.test_team.portal_show_rating = True

        rating = self.env['rating.rating'].create({
            **self.default_rating_vals,
            'rating': 5,
            'rated_partner_id': self.helpdesk_user.partner_id.id,
            'res_id': self.test_team_ticket2.id,
        })

        yesterday = date.today() - relativedelta(days=1)
        yesterday_str = f'{yesterday.year}-{yesterday.month}-{yesterday.day}'
        self.env.cr.execute("UPDATE rating_rating SET create_date=%s, write_date=%s WHERE id=%s", (yesterday_str, yesterday_str, rating.id))
        rating.invalidate_recordset(['create_date', 'write_date'])

        self.authenticate('partner_1', 'partner_1')
        res = self.url_open(f"/helpdesk/rating/{self.test_team.id}")

        self.assertEqual(res.status_code, 200, 'The request should be successful.')
        self.assertRegex(res.text, f"<img.+alt=\"{self.test_team_ticket2.name}", 'The rating should be displayed on the page.')

    def test_helpdesk_dashboard(self):
        """ Test the rating stat displayed in the dashboard for the current user.

            Test Cases:
            ==========
            1) Generate some ratings on the current date.
            2) Call the `retrieve_dashboard` method in helpdesk team model to get
               data displayed in the dashboard.
            3) Check the rating values in the dashboard data.
        """
        yesterday = date.today() - relativedelta(days=1)
        with patch.object(self.env.cr, 'now', lambda: yesterday):
            ratings = self.env['rating.rating'].create([
                {
                    **self.default_rating_vals,
                    'rating': 5,
                    'rated_partner_id': self.helpdesk_user.partner_id.id,
                    'res_id': self.test_team_ticket2.id,
                },
                {
                    **self.default_rating_vals,
                    'rating': 3,
                    'rated_partner_id': self.helpdesk_manager.partner_id.id,
                    'res_id': self.test_team_ticket1.id,
                },
            ])

        HelpdeskTeam = self.env['helpdesk.team']
        self.assertTrue(HelpdeskTeam.with_user(self.helpdesk_manager)._check_rating_feature_enabled(True))
        data = HelpdeskTeam.with_user(self.helpdesk_manager).retrieve_dashboard()
        self.assertEqual(data['today']['rating'], 0, 'The average rating of the Helpdesk Manager should be equal to 0 since no rating is done today.')
        self.assertEqual(data['7days']['rating'], 60, 'The average rating of the Helpdesk Manager should be equal to 3 / 5')

        self.assertTrue(HelpdeskTeam.with_user(self.helpdesk_user)._check_rating_feature_enabled(True))
        data = HelpdeskTeam.with_user(self.helpdesk_user).retrieve_dashboard()
        self.assertEqual(data['today']['rating'], 0, 'The average rating of the Helpdesk user should be equal to 0 since no rating is done today.')
        self.assertEqual(data['7days']['rating'], 100, 'The average rating should be equal to 5 / 5.')

        # create ratings for today
        ratings = self.env['rating.rating'].create([
            {
                **self.default_rating_vals,
                'rating': 1,
                'rated_partner_id': self.helpdesk_user.partner_id.id,
                'res_id': self.test_team_ticket2.id,
            },
            {
                **self.default_rating_vals,
                'rating': 5,
                'rated_partner_id': self.helpdesk_manager.partner_id.id,
                'res_id': self.test_team_ticket1.id,
            },
        ])
        ratings.invalidate_recordset()
        data = HelpdeskTeam.with_user(self.helpdesk_manager).retrieve_dashboard()
        self.assertEqual(data['today']['rating'], 100, 'The average rating of the Helpdesk Manager user should be equal to 5 / 5')
        self.assertEqual(data['7days']['rating'], 80, 'The average rating of the Helpdesk Manager user should be equal to 4 / 5')

        data = HelpdeskTeam.with_user(self.helpdesk_user).retrieve_dashboard()
        self.assertEqual(data['today']['rating'], 20, 'The average rating should be equal to 1 / 5.')
        self.assertEqual(data['7days']['rating'], 60, 'The average rating should be equal to 3 / 5.')

    def test_email_rating_template(self):
        self.stage_done.template_id = self.env.ref('helpdesk.rating_ticket_request_email_template')

        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test ticket',
            'team_id': self.test_team.id,
            'partner_id': self.partner_1.id,
            'stage_id': self.stage_progress.id,
        })
        self.flush_tracking()

        with self.mock_mail_gateway():
            ticket.with_user(self.helpdesk_manager).write({'stage_id': self.stage_done.id})
            self.flush_tracking()

        mail = self.env['mail.mail'].search([('email_from', '=', self.test_team.alias_email_from), ('recipient_ids', 'in', self.partner_1.id)])
        self.assertTrue(mail, 'An email from the team email alias should have been sent to the partner')
