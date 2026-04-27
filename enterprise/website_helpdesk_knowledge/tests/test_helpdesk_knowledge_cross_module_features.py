# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from markupsafe import Markup

from odoo.tests.common import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'knowledge', 'knowledge_tour')
class TestHelpdeskKnowledgeCrossModuleFeatures(HttpCase):
    """
    This test suit will test the "cross-module" features of Knowledge.
    """
    @classmethod
    def setUpClass(cls):
        super(TestHelpdeskKnowledgeCrossModuleFeatures, cls).setUpClass()
        cls.admin = cls.env.ref('base.user_admin')
        cls.admin.signature = Markup("<span>-- <br/>Mitchell Admin</span>")

        with mute_logger('odoo.models.unlink'):
            cls.env['knowledge.article'].search([]).unlink()

        article = cls.env['knowledge.article'].create({
            'name': 'EditorCommandsArticle',
            'body': Markup("""
                <p><br></p>
                <div class="o_knowledge_embedded_clipboard" data-embedded="clipboard">
                    <div class="d-flex">
                        <div class="o_embedded_clipboard_label align-middle">Clipboard</div>
                    </div>
                    <div data-embedded-editable="clipboardContent">
                        <p>Hello world</p>
                    </div>
                </div>
                <p><br></p>
            """),
            'is_article_visible_by_everyone': True,
            'favorite_ids': [(0, 0, {
                'user_id': cls.admin.id
            })],
        })
        cls.env['ir.attachment'].create({
            'datas': base64.b64encode(b'Content'),
            'name': 'Onboarding',
            'mimetype': 'text/plain',
            'res_id': article.id,
            'res_model': 'knowledge.article',
        })
        cls.env['helpdesk.ticket'].create({
            "name": "Test Ticket",
            "team_id": cls.env.ref('helpdesk.helpdesk_team1').id,
            "user_id": cls.env.ref('base.user_admin').id,
            "partner_id": cls.env.ref('base.user_admin').partner_id.id,
            "stage_id": cls.env.ref('helpdesk.stage_new').id,
            "kanban_state": 'done',
            "description": 'Test Description',
        })

    # Embedded view block:

    def test_helpdesk_insert_graph_view_in_knowledge(self):
        """This tour will check that the user can insert a graph view in an article."""
        self.start_tour('/odoo/action-helpdesk.helpdesk_ticket_analysis_action',
            'helpdesk_insert_graph_view_in_knowledge', login='admin')

    def test_helpdesk_insert_kanban_view_link_in_knowledge(self):
        """This tour will check that the user can insert a view link in an article."""
        self.start_tour('/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_insert_kanban_view_link_in_knowledge', login='admin')

    # File block:

    def test_helpdesk_pick_file_as_attachment_from_knowledge(self):
        self.start_tour('/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_file_as_attachment_from_knowledge', login='admin')

    def test_helpdesk_pick_file_as_message_attachment_from_knowledge(self):
        self.start_tour('/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_file_as_message_attachment_from_knowledge', login='admin')

    # Template block:

    def test_helpdesk_pick_template_as_description_from_knowledge(self):
        self.start_tour('/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_template_as_description_from_knowledge', login='admin')

    def test_helpdesk_pick_template_as_message_from_knowledge(self):
        self.start_tour('/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
            'helpdesk_pick_template_as_message_from_knowledge', login='admin')
