"""What a consumer of both rating mixins reads: pinned on project, which
carries `mixin.rating.parent` and, through mail.thread, a rated `rating_ids`."""

from odoo.tests import TransactionCase, tagged

from odoo.addons.rating.tests.test_rating_mixin_collision import RATED_FIELDS


@tagged("post_install", "-at_install")
class TestRatingMixinsOnProject(TransactionCase):
    def test_a_rated_model_carries_the_rated_vocabulary(self):
        # `rating_ids` reaches a rated model through rating's mixin.mail.thread
        # extension, not through mixin.rating itself.
        rated = self.env["project.task"]._fields
        for name in RATED_FIELDS:
            with self.subTest(field=name):
                self.assertIn(name, rated)

    def test_a_parent_consumer_resolves_both_vocabularies_independently(self):
        """`project.project` carries the parent mixin and, through mail.thread,
        a `rating_ids` scoped to ratings of the project itself. Both survive,
        and they are no longer the same field wearing one name."""
        project = self.env["project.project"]
        self.assertEqual(
            project._fields["rating_child_ids"].inverse_name, "parent_res_id"
        )
        self.assertEqual(project._fields["rating_ids"].inverse_name, "res_id")

    def test_the_percentage_depends_on_the_average_it_derives_from(self):
        consumer = self.env["project.project"]
        depends = self.env.registry.field_depends[
            consumer._fields["rating_child_avg_percentage"]
        ]
        self.assertIn("rating_child_avg", tuple(depends))

    def test_the_percentage_still_tracks_the_average_it_derives_from(self):
        project = self.env["project.project"].create({"name": "Rating parent"})
        self.assertEqual(
            project.rating_child_avg_percentage, project.rating_child_avg / 5
        )
