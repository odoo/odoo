# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import HttpCase, tagged

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.addons.website_forum.tests.common import TestForumCommon


@tagged('post_install', '-at_install')
class websiteHelpdeskForumUi(HelpdeskCommon, TestForumCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_team.use_website_helpdesk_forum = True
        cls._activate_multi_website()

        cls.env['forum.post'].create({
            'name': 'Very Smart Question',
            'forum_id': cls.env.ref('website_forum.forum_help').id,
        })

    def test_website_helpdesk_forum_tour(self):
        partner = self.env['res.partner'].create({
            'name': 'Jean-Luc',
            'email': 'jean-luc@opoo.com',
        })

        helpdesk_user = self.env['res.users'].create({
            'partner_id': partner.id,
            'name': 'Test User',
            'login': 'testuser@example.com',
            'password': 'testpass',
            'groups_id': [Command.link(self.env.ref('helpdesk.group_helpdesk_manager').id)],
        })

        forum = self.env.ref('website_forum.forum_help')
        self.test_team['website_forum_ids'] = [Command.link(forum.id)]
        helpdesk_user.karma = forum.karma_post + 1
        self.start_tour("/", 'website_helpdesk_forum_tour', login=helpdesk_user.login)
