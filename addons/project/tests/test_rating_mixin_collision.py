"""The two rating mixins ask different questions and no longer share an answer."""

from odoo.tests import TransactionCase, tagged

# `mixin.rating` answers "how is THIS record rated", off rating.rating.res_id.
RATED_FIELDS = (
    "rating_ids",
    "rating_count",
    "rating_avg",
    "rating_percentage_satisfaction",
)
# `mixin.rating.parent` answers "how are the records BELOW it rated", off
# rating.rating.parent_res_id. Same five questions, a vocabulary that says so.
PARENT_FIELDS = (
    "rating_child_ids",
    "rating_child_count",
    "rating_child_avg",
    "rating_child_percentage_satisfaction",
    "rating_child_avg_percentage",
)


@tagged("post_install", "-at_install")
class TestRatingMixinCollision(TransactionCase):
    def test_the_two_mixins_share_no_field_name(self):
        """The invariant the rename bought, and the one worth guarding.

        While they shared `rating_ids`, `rating_count`, `rating_avg` and
        `rating_percentage_satisfaction`, a model carrying both got one mixin's
        question and the other's answer, and nothing in the name said which. It
        cost three separate workarounds before it was named: a redeclaration on
        `project.project`, a direct `rating.rating` search inside this mixin's
        own `write`, and a compute that overwrote three fields it no longer
        owned.
        """
        parent = self.env["mixin.rating.parent"]._fields
        rated = self.env["mixin.rating"]._fields
        shared = sorted(set(parent) & set(rated) & set(RATED_FIELDS + PARENT_FIELDS))
        self.assertFalse(
            shared,
            "the rating mixins mean different things by these names: %s" % shared,
        )

    def test_each_mixin_still_declares_its_own_vocabulary(self):
        parent = self.env["mixin.rating.parent"]._fields
        for name in PARENT_FIELDS:
            with self.subTest(field=name):
                self.assertIn(name, parent)
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

    def test_rating_child_avg_percentage_is_not_computed_beside_its_average(self):
        """Kept from the defect that opened this: sharing a compute let reading
        one field silently rewrite the others, reproduced as 5.0 becoming 1.0 on
        one record in one transaction with no write between the reads."""
        parent = self.env["mixin.rating.parent"]._fields
        self.assertNotEqual(
            parent["rating_child_avg_percentage"].compute,
            parent["rating_child_avg"].compute,
        )
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
