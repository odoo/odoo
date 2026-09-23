from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.base.tests.common import converted_reach


@tagged("post_install", "-at_install")
class TestForumOfficer(TransactionCase):
    def test_an_elearning_officer_reaches_every_forum_post_and_tag(self):
        forum = self.env["forum.forum"].create(
            {
                "name": "Restricted Course Forum",
                "privacy": "private",
                "authorized_group_id": self.env.ref("base.group_system").id,
            }
        )
        tag = self.env["forum.tag"].create(
            {"name": "Officer Tag", "forum_id": forum.id}
        )
        post = self.env["forum.post"].create(
            {
                "name": "Officer Question",
                "content": "Who reads this?",
                "forum_id": forum.id,
                "tag_ids": [(6, 0, tag.ids)],
            }
        )
        officer = new_test_user(
            self.env,
            login="forum_elearning_officer",
            groups="base.group_user,website_slides.group_website_slides_officer",
        )
        for record in (post, tag):
            with self.subTest(model=record._name):
                self.assertEqual(
                    record.with_user(officer).search([("id", "=", record.id)]), record
                )
                for operation in ("read", "write", "unlink"):
                    self.assertEqual(
                        converted_reach(self.env, record._name, officer, operation)
                        & record,
                        record,
                    )
