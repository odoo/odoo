# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteHrRecruitmentDuplicateApplications(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_1, cls.job_2 = cls.env["hr.job"].create(
            [
                {"name": "job 1", "is_published": True},
                {"name": "job 2", "is_published": True},
            ],
        )
        cls.applicant_data_1 = {
            "partner_name": "Test Applicant",
            "email_from": "test@example.com",
            "partner_phone": "1234",
            "linkedin_profile": "linkedin.com/in/test-applicant",
            "job_id": cls.job_1.id,
        }
        cls.applicant_data_2 = {
            "partner_name": "Totally Not Test Applicant",
            "email_from": "totally.not.test.applicant@example.com",
            "partner_phone": "5678",
            "linkedin_profile": "linkedin.com/in/totally-not-test-applicant",
            "job_id": cls.job_1.id,
        }
        cls.test_applicant = cls.env["hr.applicant"].create(cls.applicant_data_1)

        cls.refuse_reason = cls.env["hr.applicant.refuse.reason"].create([{"name": "Refused"}])

    def test_detects_a_full_duplicate_of_an_ongoing_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        ongoing applicant with the same information exists.
        """
        res = self.url_open("/website/form/hr.applicant", data=self.applicant_data_1)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Ongoing Application",
            "The activity summary should indicate that this is a duplicate of an ongoing application",
        )

    def test_detects_an_email_duplicate_of_an_ongoing_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        ongoing applicant with the same email exists.
        """
        new_applicant_data = {
            **self.applicant_data_2,
            "email_from": self.applicant_data_1["email_from"],
        }
        res = self.url_open("/website/form/hr.applicant", data=new_applicant_data)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Ongoing Application",
            "The activity summary should indicate that this is a duplicate of an ongoing application",
        )

    def test_detects_a_phone_duplicate_of_an_ongoing_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        ongoing applicant with the same phone number exists.
        """
        new_applicant_data = {
            **self.applicant_data_2,
            "partner_phone": self.applicant_data_1["partner_phone"],
        }
        res = self.url_open("/website/form/hr.applicant", data=new_applicant_data)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Ongoing Application",
            "The activity summary should indicate that this is a duplicate of an ongoing application",
        )

    def test_detects_a_linkedin_duplicate_of_an_ongoing_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        ongoing applicant with the same linkedin exists.
        """
        new_applicant_data = {
            **self.applicant_data_2,
            "linkedin_profile": self.applicant_data_1["linkedin_profile"],
        }
        res = self.url_open("/website/form/hr.applicant", data=new_applicant_data)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Ongoing Application",
            "The activity summary should indicate that this is a duplicate of an ongoing application",
        )

    def test_detects_an_email_phone_duplicate_of_an_ongoing_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        ongoing applicant with the same email and phone exists.
        """
        new_applicant_data = {
            **self.applicant_data_2,
            "email_from": self.applicant_data_1["email_from"],
            "partner_phone": self.applicant_data_1["partner_phone"],
        }
        res = self.url_open("/website/form/hr.applicant", data=new_applicant_data)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Ongoing Application",
            "The activity summary should indicate that this is a duplicate of an ongoing application",
        )

    def test_detects_an_email_linkedin_duplicate_of_an_ongoing_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        ongoing applicant with the same email and linkedin exists.
        """
        new_applicant_data = {
            **self.applicant_data_2,
            "email_from": self.applicant_data_1["email_from"],
            "linkedin_profile": self.applicant_data_1["linkedin_profile"],
        }
        res = self.url_open("/website/form/hr.applicant", data=new_applicant_data)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Ongoing Application",
            "The activity summary should indicate that this is a duplicate of an ongoing application",
        )

    def test_detects_a_phone_linkedin_duplicate_of_an_ongoing_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        ongoing applicant with the same phone and linkedin exists.
        """
        new_applicant_data = {
            **self.applicant_data_2,
            "partner_phone": self.applicant_data_1["partner_phone"],
            "linkedin_profile": self.applicant_data_1["linkedin_profile"],
        }
        res = self.url_open("/website/form/hr.applicant", data=new_applicant_data)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Ongoing Application",
            "The activity summary should indicate that this is a duplicate of an ongoing application",
        )

    def test_detects_a_full_duplicate_of_a_refused_application(self):
        """
        Assert that a to-do activity is added to a new applicant if another
        refused applicant with the same information exists.
        """
        # Refuse the existing applicant
        self.test_applicant.write(
            {
                "refuse_reason_id": self.refuse_reason,
                "active": False,
                "refuse_date": datetime.now(),
            },
        )

        res = self.url_open("/website/form/hr.applicant", data=self.applicant_data_1)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Refused Application",
            "The activity summary should indicate that this is a duplicate of an refused application",
        )

    def test_does_not_detect_a_full_duplicate_of_a_refused_application_past_6_months(self):
        """
        Assert that a to-do activity is NOT added to a new applicant if another
        refused applicant with the same information exists that was refused more
        than six months ago.
        """
        # Refuse the existing applicant
        self.test_applicant.write(
            {
                "refuse_reason_id": self.refuse_reason,
                "active": False,
                "refuse_date": datetime.now() - relativedelta(months=6, days=1),
            },
        )

        res = self.url_open("/website/form/hr.applicant", data=self.applicant_data_1)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertFalse(applicant_activities, "The applicant should not have any linked activities")

    def test_does_not_detect_a_full_duplicate_for_a_different_job(self):
        """
        Assert that a to-do activity is NOT added to a new applicant if another
        refused applicant with the same information except a different job exists.
        """
        new_applicant_data = {
            **self.applicant_data_1,
            "job_id": self.job_2.id,
        }
        res = self.url_open("/website/form/hr.applicant", data=new_applicant_data)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids

        self.assertEqual(new_applicant.application_count, 2, "The applicant should have 2 related applications")
        self.assertFalse(applicant_activities, "The applicant should not have any linked activities")

    def test_prioritizes_a_refused_message_over_ongoing(self):
        """
        Assert that if there are two existing applicants, and one of them is
        refused, add only one activity and only for the refused applicant.
        """
        # Create a new ongoing applicant
        self.env["hr.applicant"].create(self.applicant_data_1)
        # Refuse the existing applicant
        self.test_applicant.write(
            {
                "refuse_reason_id": self.refuse_reason,
                "active": False,
                "refuse_date": datetime.now(),
            },
        )

        res = self.url_open("/website/form/hr.applicant", data=self.applicant_data_1)
        new_applicant = self.env["hr.applicant"].browse(res.json().get("id"))
        applicant_activities = new_applicant.activity_ids
        self.assertEqual(new_applicant.application_count, 3, "The applicant should have 3 related applications")
        self.assertTrue(applicant_activities, "The applicant should have a linked activity")
        self.assertEqual(len(applicant_activities), 1, "The applicant should only have one linked activity")
        self.assertEqual(
            applicant_activities.mapped("summary")[0],
            "Potential Duplicate Detected: Refused Application",
            "The activity summary should indicate that this is a duplicate of a refused application",
        )
