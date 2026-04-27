# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from markupsafe import Markup

from odoo.tests.common import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged('post_install', '-at_install', 'knowledge', 'knowledge_tour')
class TestKnowledgeEditorCommands(HttpCaseWithUserDemo):
    """
    This test suit run tours to test the new editor commands of Knowledge.
    """
    @classmethod
    def setUpClass(cls):
        super(TestKnowledgeEditorCommands, cls).setUpClass()
        # remove existing articles to ease tour management
        cls.env['knowledge.article'].search([]).unlink()

        [cls.article, cls.linked_article] = cls.env['knowledge.article'].create([{
            'name': 'EditorCommandsArticle',
            'body': Markup('<p>EditorCommandsArticle Content<br></p>'),
            'sequence': 1,
            'full_width': True,
            'internal_permission': 'read',
            'article_member_ids': [(0, 0, {
                'partner_id': cls.env.ref('base.partner_admin').id,
                'permission': 'write',
            })],
            'child_ids': [(0, 0, {
                'name': 'Child 1',
                'sequence': 3,
                'is_article_item': True,
            }), (0, 0, {
                'name': 'Child 2',
                'sequence': 4,
                'is_article_item': True,
            })],
            'favorite_ids': [(0, 0, {
                'user_id': cls.env.ref('base.user_admin').id,
            })],
            'is_article_visible_by_everyone': True,
        }, {
            'name': 'LinkedArticle',
            'body': Markup('<p><br></p>'),
            'sequence': 2,
            'is_article_visible_by_everyone': True,
        }])

        partner_ids = cls.env['res.partner'].create({'name': 'HelloWorldPartner', 'email': 'helloworld@part.ner'}).ids
        cls.article.message_subscribe(partner_ids)

        cls.env['ir.attachment'].create({
            'datas': base64.b64encode(b'Content'),
            'name': 'Onboarding.txt',
            'mimetype': 'text/plain',
            'res_id': cls.article.id,
            'res_model': 'knowledge.article',
        })

    def test_knowledge_article_commands_tour(self):
        """ Test the various commands in the editor as admin user.
        Then access created embed views in readonly mode for extra checks. """
        self.start_tour('/odoo', 'knowledge_article_commands_tour', login='admin')

        # Check that the icon selected from the kanban card has been saved
        quik_create_article = self.env['knowledge.article'].search([("name", "=", "New Quick Create Item")])
        self.assertEqual(quik_create_article.icon, "🤩")

        self.start_tour('/odoo', 'knowledge_article_commands_readonly_tour', login='demo')

    def test_knowledge_calendar_command_tour(self):
        """Test the /calendar command in the editor"""
        self.start_tour('/odoo', 'knowledge_calendar_command_tour', login='admin')
