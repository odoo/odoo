# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_forum.tests.common import TestForumCommon


@tagged("post_install", "-at_install")
class TestWebsiteForumJsonLd(TestForumCommon):
    def test_question_to_structured_data(self):
        json_ld = self.post._to_structured_data()
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "QAPage")
        self.assertEqual(markup_data["mainEntity"]["@type"], "Question")
        self.assertEqual(markup_data["mainEntity"]["name"], self.post.name)
        self.assertEqual(markup_data["mainEntity"]["suggestedAnswer"]["@type"], "Answer")

    def test_answer_to_structured_data_is_none(self):
        self.assertFalse(self.answer._to_structured_data())

    def test_question_without_answers_has_no_schema(self):
        question_without_answers = self.env["forum.post"].create({
            "name": "Question Without Answers",
            "content": "No answer yet",
            "forum_id": self.forum.id,
        })

        self.assertFalse(question_without_answers._to_structured_data())
