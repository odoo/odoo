# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.addons.website_forum.tests.common import TestForumCommon

class TestHelpdeskForum(HelpdeskCommon, TestForumCommon):
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

    def test_share_ticket(self):
        self.assertTrue(self.ticket.can_share_forum, 'Ticket should be able to be shared on the forums.')

        form = Form(self.env['helpdesk.ticket.select.forum.wizard'].with_context({'active_id': self.ticket.id}))
        wizard = form.save()

        wizard.tag_ids = [Command.create({'name': 'tag_1', 'forum_id': self.forum.id}), Command.create({'name': 'tag_2', 'forum_id': self.forum.id})]
        post = wizard._create_forum_post()

        self.assertEqual(post.name, self.ticket_name, 'The created post should have the same name as the ticket.')
        self.assertEqual(post.plain_content, self.ticket_description, 'The created post should have the same description as the ticket.')
        self.assertEqual(post.ticket_id, self.ticket, 'The created post should point to the ticket.')
        self.assertEqual(len(post.tag_ids), 2, 'The created post should have the tags defined in the wizard.')

    def test_show_knowledge_base_forum(self):
        # see /website_helpdesk_forum:HelpdeskTeam._compute_show_knowledge_base_forum() for more info
        test_team_public = self.test_team.with_user(self.env.ref('base.public_user'))
        forums = self.env['forum.forum'].search([])

        self.test_team.use_website_helpdesk_forum = False
        self.assertFalse(test_team_public.show_knowledge_base_forum, 'This team does not use Forums')

        self.test_team.use_website_helpdesk_forum = True
        self.test_team.website_forum_ids = False
        forums.privacy = 'private'
        self.assertFalse(test_team_public.show_knowledge_base_forum, 'User does not have access to any forum')

        self.test_team.website_forum_ids = False
        forums[0].privacy = 'public'
        self.assertTrue(test_team_public.show_knowledge_base_forum, 'User has access to a forum')

        self.test_team.website_forum_ids = forums
        self.assertTrue(test_team_public.show_knowledge_base_forum, 'User has access to one of the help forums')

        self.test_team.website_forum_ids = forums[1]
        forums[1].privacy = 'private'
        self.assertFalse(test_team_public.show_knowledge_base_forum, 'User does not have access to any of the help forums')

    def test_top_forum_posts(self):
        # We first create a new nice, interesting forum for our helpdesk team
        forum = self.env['forum.forum'].create({
            'name': 'Discussions on Mushrooms',
        })
        self.test_team['website_forum_ids'] = forum

        # Then we create 7 different forum posts for our forum
        forum_posts = self.env['forum.post'].create([{
            'name': f'This is forum post number {post_record}',
            'forum_id': forum.id,
        } for post_record in range(1, 8)])

        # Then we need to create some users which will vote the forum posts
        # We create 28 users because we need one for each vote.
        forum_users = self.env['res.users'].create([{
            'name': f"Theodore the {index}'th",
            'login': f'usr{index}',
            'email': f'user{index}@example.com',
        } for index in range(0, 28)])

        # Finally it's time to create the votes for each of the forum posts
        forum_user_ids = forum_users.ids
        self.env['forum.post.vote'].create([{
            'post_id': forum_value.id,
            'user_id': forum_user_ids.pop(),
            'vote': '1',
        } for index, forum_value in enumerate(forum_posts) for _ in range(index+1)])

        self.assertEqual(self.test_team.top_forum_posts, forum_posts[6:1:-1], 'The top posts should be the ones with the most votes, in this case the last 5 from last to first')
