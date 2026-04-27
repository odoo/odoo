# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.knowledge.tests.test_knowledge_article_business import KnowledgeCommonBusinessCase


@tagged('post_install', '-at_install', 'knowledge', 'knowledge_tour', 'knowledge_comments')
class TestKnowledgeArticleTours(HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        """ The test article body contains custom selectors to ease the test steps as well as a
         pre-existing comment on the second paragraph. """

        super().setUpClass()

        cls.test_article = cls.env['knowledge.article'].create([{
            'name': 'Sepultura',
            'is_article_visible_by_everyone': True,
            'internal_permission': 'write',
        }])

        cls.test_article_thread = cls.env['knowledge.article.thread'].create({
            'article_id': cls.test_article.id,
            'article_anchor_text': f"""
            <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="1" data-oe-type="threadBeaconStart" data-res_id="{cls.test_article.id}" data-oe-model="knowledge.article" />
                    Lorem ipsum dolor
            <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="1" data-oe-type="threadBeaconEnd" data-res_id="{cls.test_article.id}" data-oe-model="knowledge.article"/>
            """,
        })
        cls.test_article_thread.message_post(
            body="Marc, can you check this?",
            message_type="comment"
        )

        cls.test_article.write({
            'body': f"""
                <p class="o_knowledge_tour_first_paragraph">
                    Lorem ipsum dolor sit amet,
                </p>
                <p>
                    <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" data-id="{cls.test_article_thread.id}" data-oe-type="threadBeaconStart" data-res_id="{cls.test_article.id}" data-oe-model="knowledge.article"></a>
                    Lorem ipsum dolor commented
                    <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" data-id="{cls.test_article_thread.id}" data-oe-type="threadBeaconEnd" data-res_id="{cls.test_article.id}" data-oe-model="knowledge.article"></a>
                </p>
            """
        })

    def test_knowledge_article_comments(self):
        self.start_tour('/odoo', 'knowledge_article_comments', login='demo')

        # assert messages and resolved status
        self.assertTrue(self.test_article_thread.is_resolved)
        expected_messages = [
            "Marc, can you check this?",
            "Sure thing boss, all done!",
            "Oops forgot to mention, will be done in task-112233",
        ]

        for message, expected_message in zip(
            self.test_article_thread.message_ids
                .filtered(lambda message: message.message_type == 'comment')
                .sorted('create_date').mapped('body'),
            expected_messages
        ):
            self.assertIn(expected_message, message)

        new_thread = self.env['knowledge.article.thread'].search([
            ('article_id', '=', self.test_article.id),
            ('id', '!=', self.test_article_thread.id),
        ])
        self.assertEqual(len(new_thread), 1)
        self.assertEqual(len(new_thread.message_ids), 1)
        self.assertIn("My Knowledge Comment", new_thread.message_ids[0].body)


class TestKnowledgeArticleThreadCrud(KnowledgeCommonBusinessCase):

    def test_knowledge_article_thread_create_w_unsafe_anchors(self):
        new_thread = self.env['knowledge.article.thread'].create({
            'article_id': self.article_workspace.id,
            'article_anchor_text': f"""
                <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="1" data-oe-type="threadBeaconStart" data-res_id="{self.article_workspace.id}" data-oe-model="knowledge.article" />
                    <iframe src="www.pwned.com">Anchor</iframe><script src="www.extrapwned.com"/>Text
                <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="1" data-oe-type="threadBeaconEnd" data-res_id="{self.article_workspace.id}" data-oe-model="knowledge.article"/>
            """,
        })
        self.assertEqual("Anchor Text", new_thread.article_anchor_text)

        new_thread.write({
            'article_anchor_text': f"""
                <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="3" data-oe-type="threadBeaconStart" data-res_id="{self.article_workspace.id}" data-oe-model="knowledge.article" />
                    <iframe src="javascript:alert(1)">Should be</iframe><script src="www.extrapwned.com"/>Purified
                <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="3" data-oe-type="threadBeaconEnd" data-res_id="{self.article_workspace.id}" data-oe-model="knowledge.article"/>
            """
        })
        self.assertEqual("Should be Purified", new_thread.article_anchor_text)


class TestKnowledgeArticleThreadMail(KnowledgeCommonBusinessCase):

    def test_knowledge_article_thread_message_post_filtered_partners(self):
        new_thread = self.env['knowledge.article.thread'].create({
            'article_id': self.article_workspace.id,
            'article_anchor_text': f"""
                <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="1" data-oe-type="threadBeaconStart" data-res_id="{self.article_workspace.id}" data-oe-model="knowledge.article" />
                    <iframe src="www.pwned.com">Anchor</iframe><script src="www.extrapwned.com"/>Text
                <a class="oe_unremovable oe_thread_beacon" data-oe-protected="true" contenteditable="false" data-id="1" data-oe-type="threadBeaconEnd" data-res_id="{self.article_workspace.id}" data-oe-model="knowledge.article"/>
            """,
        })
        self.env["mail.followers"]._insert_followers("knowledge.article.thread", new_thread.ids, (self.partner_portal + self.env.user.partner_id + self.partner_admin).ids)
        message_posted = new_thread.message_post(body="Prout")

        self.assertFalse(message_posted.partner_ids, "No specific partners to notify")

        message_posted = new_thread.message_post(body="Prout", partner_ids=(self.partner_portal + self.partner_admin).ids)
        self.assertEqual(message_posted.partner_ids.ids, (self.partner_portal + self.partner_admin).ids, "Only specifically tagged partners should be notified")
