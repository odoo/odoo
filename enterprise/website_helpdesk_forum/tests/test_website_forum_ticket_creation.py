# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_forum.tests.common import TestForumCommon
from odoo.addons.website_helpdesk_forum.controllers.website_forum import WebsiteForumHelpdesk


class TestHelpdeskForumTicketCreation(HttpCase, TestForumCommon, HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_team.use_website_helpdesk_forum = True
        cls.ticket_name = 'Help Me'
        cls.ticket_description = 'Please Help'

        cls.ticket = cls.env['helpdesk.ticket'].create({
            'name': cls.ticket_name,
            'description': cls.ticket_description,
            'team_id': cls.test_team.id,
        })
        cls._activate_multi_website()

    def test_create_ticket_through_the_post(self):
        """ Check if a ticket is created through the post.

        Steps:
            1. Install the module `website_helpdesk_forum`.
            2. Create a team and activate Community Forum.
            3. Go to the website.
            4. Open the forum.
            5. Create a post.
            6. Check if the "Create Ticket" button is visible in the post.
            7. Verify that the post is linked with the ticket.
            8. Check if the "View Ticket" button is visible in the post.
        """
        password = 'Pl1bhD@2!kXZ'
        login_user = self.env['res.users'].create({
            "email": "test1@example.com",
            "login": "test1",
            "name": "test1",
            "password": password,
        })
        self.authenticate(login_user.login, password)

        forum = self.env['forum.forum'].create({
            'name': 'Discussions on Mushrooms',
        })
        self.test_team['website_forum_ids'] = forum
        forum_post = self.env['forum.post'].create({
            'name': 'This is forum post',
            'forum_id': forum.id,
        })
        slug = self.env['ir.http']._slug
        url = f'/forum/{slug(forum)}/{slug(forum_post)}/get-forum-data'
        forum_data = self.make_jsonrpc_request(url)

        with self.with_user(login_user.login), MockRequest(self.env, website=self.base_website):
            template_vals = WebsiteForumHelpdesk()._prepare_question_template_vals(forum=forum, post={}, question=forum_post)
            self.assertTrue(not template_vals.get('question').show_ticket and not template_vals.get('answer', False)
                and template_vals.get('show_create_ticket'), 'The Create Ticket button should be visible.')
            forum.create_ticket(forum_post.id, {
                'post_creator_id': forum_data.get('post_creator_id'),
                'post_creator_name': forum_data.get('post_creator_name'),
                'post_description': forum_data.get('post_description'),
                'post_title': forum_data.get('post_title'),
                'team_id': forum_data.get('teams')[0][0],
            })

            self.assertEqual(forum_post.ticket_id.team_id, self.test_team, 'The ticket is linked with the forum post.')

        with self.with_user(login_user.login), MockRequest(self.env, website=self.base_website):
            template_vals = WebsiteForumHelpdesk()._prepare_question_template_vals(forum=forum, post={}, question=forum_post)
            self.assertTrue(template_vals.get('question').show_ticket, 'The View Ticket button should be visible.')
