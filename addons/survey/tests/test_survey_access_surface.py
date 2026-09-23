from psycopg.errors import UniqueViolation

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.survey.tests import common


@tagged("post_install", "-at_install", "functional")
class TestSurveyAccessSurface(common.TestSurveyCommon, HttpCase):
    """The public entry points, and the guards that were missing from three of them."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invite_only = cls.env["survey.survey"].create(
            {
                "title": "Invite only",
                "access_mode": "token",
                "slug": "invite-only-slug",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (0, 0, {"title": "Secret", "question_type": "char_box"})
                ],
            }
        )
        cls.public_survey = cls.env["survey.survey"].create(
            {
                "title": "Public",
                "access_mode": "public",
                "slug": "public-slug",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (0, 0, {"title": "Open", "question_type": "char_box"})
                ],
            }
        )

    def test_slug_does_not_hand_out_an_invite_only_token(self):
        response = self.url_open("/s/invite-only-slug", allow_redirects=False)
        self.assertNotIn(
            self.invite_only.access_token,
            response.headers.get("Location", ""),
            "the slug branch must not disclose the survey's bearer token",
        )

    def test_slug_still_works_for_a_public_survey(self):
        response = self.url_open("/s/public-slug", allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn(self.public_survey.access_token, response.headers["Location"])

    def test_slug_is_unique(self):
        with self.assertRaises(UniqueViolation):
            with self.env.cr.savepoint():
                self.env["survey.survey"].create(
                    {"title": "Clash", "slug": "public-slug"}
                )

    def test_blank_slug_is_stored_as_null(self):
        """Otherwise the second survey with an empty slug trips the unique constraint."""
        first = self.env["survey.survey"].create({"title": "No slug 1", "slug": ""})
        second = self.env["survey.survey"].create({"title": "No slug 2", "slug": "  "})
        self.assertFalse(first.slug)
        self.assertFalse(second.slug)

    def test_slug_format_is_checked(self):
        for bad in ("has spaces", "trailing-", "double--hyphen", "sla/sh", "accént"):
            with self.subTest(slug=bad), self.assertRaises(ValidationError):
                with self.env.cr.savepoint():
                    self.env["survey.survey"].create({"title": "Bad", "slug": bad})

    def test_slug_case_and_padding_are_normalised_rather_than_rejected(self):
        survey = self.env["survey.survey"].create(
            {"title": "Cased", "slug": "  My-Slug  "}
        )
        self.assertEqual(survey.slug, "my-slug")

    def test_background_image_of_an_archived_survey_is_not_public(self):
        self.public_survey.action_archive()
        response = self.url_open(
            f"/survey/{self.public_survey.access_token}/get_background_image"
        )
        self.assertEqual(response.status_code, 404)

    def test_background_image_of_a_live_survey_is_still_served(self):
        response = self.url_open(
            f"/survey/{self.public_survey.access_token}/get_background_image"
        )
        self.assertEqual(response.status_code, 200)

    def test_cross_tabulation_refuses_a_restricted_officer(self):
        """The route used to browse() a raw id; only an incidental read stopped this."""
        owner = common.mail_new_test_user(
            self.env,
            login="xtab_owner",
            groups="base.group_user,survey.group_survey_user",
        )
        intruder = common.mail_new_test_user(
            self.env,
            login="xtab_intruder",
            groups="base.group_user,survey.group_survey_user",
        )
        survey = self.env["survey.survey"].create(
            {
                "title": "Restricted",
                "access_mode": "public",
                "questions_layout": "one_page",
                "user_id": owner.id,
                "restrict_user_ids": [(6, 0, [owner.id])],
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "Band",
                            "sequence": 1,
                            "question_type": "simple_choice",
                            "suggested_answer_ids": [(0, 0, {"value": "high"})],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "title": "Leaving",
                            "sequence": 2,
                            "question_type": "simple_choice",
                            "suggested_answer_ids": [(0, 0, {"value": "yes"})],
                        },
                    ),
                ],
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            survey.with_user(intruder).check_access("read")

    def test_cross_tabulation_counts_every_answer_of_a_multi_choice(self):
        survey = self.env["survey.survey"].create(
            {
                "title": "Cross tab",
                "access_mode": "public",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "Multi",
                            "sequence": 1,
                            "question_type": "multiple_choice",
                            "suggested_answer_ids": [
                                (0, 0, {"value": "A"}),
                                (0, 0, {"value": "B"}),
                            ],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "title": "Single",
                            "sequence": 2,
                            "question_type": "simple_choice",
                            "suggested_answer_ids": [(0, 0, {"value": "X"})],
                        },
                    ),
                ],
            }
        )
        multi, single = survey.question_ids
        answer = survey._create_answer(email="xtab@test.com")
        answer._mark_in_progress()
        answer._save_lines(multi, [a.id for a in multi.suggested_answer_ids])
        answer._save_lines(single, single.suggested_answer_ids[0].id)
        answer._mark_done()
        self.env.flush_all()

        result = survey._prepare_cross_tabulation(multi.id, single.id)
        self.assertEqual(
            sorted(result["row_labels"]),
            ["A", "B"],
            "both selected answers must appear, not just the last line",
        )
        self.assertEqual(result["grand_total"], 2)


@tagged("post_install", "-at_install", "functional")
class TestConversationalNavigation(common.TestSurveyCommon):
    """questions_layout_effective maps conversational; one template did not use it."""

    def test_conversational_can_go_forward(self):
        for layout, expected in (
            ("page_per_question", True),
            ("page_per_section", True),
            ("one_page", False),
            ("conversational", True),
        ):
            survey = self.env["survey.survey"].new({"questions_layout": layout})
            with self.subTest(layout=layout):
                self.assertEqual(
                    survey.questions_layout_effective
                    in ("page_per_question", "page_per_section"),
                    expected,
                    f"{layout} navigation state is wrong",
                )

    def test_navigation_template_enables_the_arrow_for_conversational(self):
        survey = self.env["survey.survey"].create(
            {
                "title": "Conversational",
                "access_mode": "public",
                "questions_layout": "conversational",
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {"title": "First", "sequence": 1, "question_type": "char_box"},
                    ),
                    (
                        0,
                        0,
                        {"title": "Second", "sequence": 2, "question_type": "char_box"},
                    ),
                ],
            }
        )
        answer = survey._create_answer(email="conv@test.com")
        answer._mark_in_progress()
        rendered = self.env["ir.qweb"]._render(
            "survey.survey_navigation",
            {"survey": survey, "answer": answer, "survey_last": False},
        )
        self.assertNotIn(
            'disabled="disabled"',
            str(rendered),
            "a conversational survey advances like page_per_question",
        )


@tagged("post_install", "-at_install", "functional")
class TestQualityIndicators(common.TestSurveyCommon):
    """is_speeder compares a response against its siblings, so it cannot be stored."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.timed_survey = cls.env["survey.survey"].create(
            {
                "title": "Timed",
                "access_mode": "public",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (0, 0, {"title": "Q", "question_type": "char_box"})
                ],
            }
        )

    def _respond(self, seconds, tag):
        from datetime import timedelta

        from odoo import fields

        answer = self.timed_survey._create_answer(email=f"{tag}@test.com")
        answer._mark_in_progress()
        answer.start_datetime = fields.Datetime.now() - timedelta(seconds=seconds)
        answer._save_lines(self.timed_survey.question_ids[0], "x")
        answer._mark_done()
        self.env.flush_all()
        return answer

    def test_is_speeder_follows_the_median_as_it_moves(self):
        fast = [self._respond(600, f"fast{i}") for i in range(3)]
        self.env.invalidate_all()
        for answer in fast:
            self.assertFalse(
                answer.is_speeder, "600s against a 600s median is not fast"
            )

        for i in range(6):
            self._respond(6000, f"slow{i}")
        self.env.invalidate_all()
        for answer in fast:
            self.assertTrue(
                answer.is_speeder,
                "600s against a 6000s median is a speeder -- a stored column "
                "would still read False here",
            )
            self.assertEqual(answer.quality_score, 50)

    def test_is_speeder_is_searchable(self):
        fast = [self._respond(600, f"sfast{i}") for i in range(3)]
        for i in range(6):
            self._respond(6000, f"sslow{i}")
        self.env.invalidate_all()
        found = self.env["survey.user_input"].search(
            [("survey_id", "=", self.timed_survey.id), ("is_speeder", "=", True)]
        )
        self.assertEqual(set(found.ids), {a.id for a in fast})

    def test_quality_score_is_searchable(self):
        self._respond(600, "qfast")
        for i in range(6):
            self._respond(6000, f"qslow{i}")
        self.env.invalidate_all()
        low = self.env["survey.user_input"].search(
            [("survey_id", "=", self.timed_survey.id), ("quality_score", "<", 100)]
        )
        self.assertEqual(len(low), 1)
        self.assertTrue(low.is_speeder)

    def test_straight_liner_stays_stored_because_it_is_self_contained(self):
        field = self.env["survey.user_input"]._fields["is_straight_liner"]
        self.assertTrue(
            field.store,
            "it depends only on the record's own lines, so storing is right",
        )
        self.assertFalse(self.env["survey.user_input"]._fields["is_speeder"].store)


@tagged("post_install", "-at_install", "functional")
class TestQuotaReservation(common.TestSurveyCommon):
    """A quota reserves a place, but an abandoned response has to give it back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.quota_survey = cls.env["survey.survey"].create(
            {
                "title": "Quota survey",
                "access_mode": "public",
                "questions_layout": "page_per_question",
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "Pick",
                            "sequence": 1,
                            "question_type": "simple_choice",
                            "suggested_answer_ids": [
                                (0, 0, {"value": "Limited"}),
                                (0, 0, {"value": "Open"}),
                            ],
                        },
                    ),
                    (
                        0,
                        0,
                        {"title": "Later", "sequence": 2, "question_type": "char_box"},
                    ),
                ],
            }
        )
        cls.pick = cls.quota_survey.question_ids[0]
        cls.limited = cls.pick.suggested_answer_ids[0]
        cls.quota = cls.env["survey.quota"].create(
            {
                "survey_id": cls.quota_survey.id,
                "question_id": cls.pick.id,
                "answer_id": cls.limited.id,
                "limit": 1,
            }
        )

    def _pick_limited(self, tag):
        answer = self.quota_survey._create_answer(email=f"{tag}@test.com")
        answer._mark_in_progress()
        answer._save_lines(self.pick, self.limited.id)
        self.env.flush_all()
        return answer

    def test_an_in_flight_response_reserves_its_place(self):
        self._pick_limited("first")
        self.quota.invalidate_recordset()
        self.assertTrue(
            self.quota.is_full,
            "the quota must not be oversold while a response is live",
        )

    def test_an_abandoned_response_releases_its_place(self):
        from datetime import timedelta

        from odoo import fields

        abandoned = self._pick_limited("abandoned")
        self.env.cr.execute(
            "UPDATE survey_user_input SET create_date = %s WHERE id = %s",
            [
                fields.Datetime.now()
                - timedelta(hours=self.env["survey.quota"].RESERVATION_HOURS + 1),
                abandoned.id,
            ],
        )
        self.env.invalidate_all()
        self.assertFalse(
            self.quota.is_full,
            "an abandoned response must not hold a public survey's quota for good",
        )

    def test_a_completed_response_holds_its_place_indefinitely(self):
        from datetime import timedelta

        from odoo import fields

        done = self._pick_limited("done")
        done._mark_done()
        self.env.cr.execute(
            "UPDATE survey_user_input SET create_date = %s WHERE id = %s",
            [fields.Datetime.now() - timedelta(days=365), done.id],
        )
        self.env.invalidate_all()
        self.assertTrue(
            self.quota.is_full, "a completed response is what the quota is counting"
        )
