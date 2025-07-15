# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.tests import Form, tagged, TransactionCase


@tagged("recruitment")
class TestRecruitmentTalentPool(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.t_talent_pool_1, cls.t_talent_pool_2 = cls.env["hr.talent.pool"].create(
            [{"name": "Test Talent Pool 1"}, {"name": "Test Talent Pool 2"}]
        )

        cls.t_applicant_1, cls.t_applicant_2 = cls.env["hr.applicant"].create(
            [{"partner_name": "Test Applicant 1"}, {"partner_name": "Test Applicant 2"}]
        )

        cls.t_job_1, cls.t_job_2, cls.t_job_3 = cls.env["hr.job"].create(
            [
                {"name": "Job 1"},
                {"name": "Job 2"},
                {"name": "Job 3"},
            ]
        )
        cls.mail_template = cls.env['mail.template'].create({
            'name': 'Test stage template',
            'model_id': cls.env['ir.model']._get_id('hr.applicant'),
            'subject': 'Job application test',
        })

    def test_add_applicant_to_one_talent_pool(self):
        """
        Test that a applicant is duplicated and linked to a pool when creating a talent.
        """
        talent_pool_applicant = self.t_talent_pool_1.talent_ids
        self.assertFalse(talent_pool_applicant, "There should not be any applicants in the talent pool")

        wizard = Form(self.env["talent.pool.add.applicants"])
        wizard.talent_pool_ids = self.t_talent_pool_1
        wizard.applicant_ids = self.t_applicant_1
        talent_pool_applicant = wizard.save()._add_applicants_to_pool()

        self.assertTrue(
            talent_pool_applicant, "An applicant('talent') should be created when adding an applicant to a pool"
        )
        self.assertNotEqual(
            self.t_applicant_1, talent_pool_applicant, "The 'talent' and the applicant should be two different records"
        )
        self.assertEqual(
            talent_pool_applicant.talent_pool_ids,
            self.t_talent_pool_1,
            "The talent should be linked to the talent pool",
        )

    def test_add_applicant_to_multiple_talent_pools(self):
        """
        Test that a applicant is only duplicated once and linked to multiple pools when creating a talent.
        """
        wizard = Form(self.env["talent.pool.add.applicants"])
        wizard.talent_pool_ids.add(self.t_talent_pool_1)
        wizard.talent_pool_ids.add(self.t_talent_pool_2)
        wizard.applicant_ids = self.t_applicant_1
        talent_pool_applicant = wizard.save()._add_applicants_to_pool()

        self.assertTrue(
            talent_pool_applicant, "An applicant('talent') should be created when adding an applicant to a pool"
        )
        self.assertEqual(
            len(talent_pool_applicant), 1, "Exactly one 'talent' should be created when adding an applicant to a pool"
        )
        self.assertEqual(
            talent_pool_applicant.talent_pool_ids,
            self.t_talent_pool_1 | self.t_talent_pool_2,
            "The 'talent' should belong to both talent pools",
        )

    def test_add_multiple_applicants_to_multiple_talent_pools(self):
        """
        Test that multiple applicants are only duplicated once and linked to multiple pools when creating talents.
        """
        talent_pool_applicants = self.t_talent_pool_1.talent_ids | self.t_talent_pool_2.talent_ids
        self.assertFalse(talent_pool_applicants, "There should not be any applicants in the talent pools")

        with Form(self.env["talent.pool.add.applicants"]) as wizard:
            wizard.talent_pool_ids.add(self.t_talent_pool_1)
            wizard.talent_pool_ids.add(self.t_talent_pool_2)
            wizard.applicant_ids.add(self.t_applicant_1)
            wizard.applicant_ids.add(self.t_applicant_2)

        talent_pool_applicants = wizard.record._add_applicants_to_pool()

        self.assertTrue(
            talent_pool_applicants, "An applicant('talent') should be created when adding an applicant to a pool"
        )
        self.assertEqual(
            len(talent_pool_applicants),
            2,
            "Exactly two 'talents' should be created when adding two applicants to pools",
        )
        for applicant in talent_pool_applicants:
            self.assertEqual(
                applicant.talent_pool_ids,
                self.t_talent_pool_1 | self.t_talent_pool_2,
                f"Talent {applicant.partner_name} should belong to two talent pools",
            )

    def test_add_applicant_is_only_duplicated_once(self):
        """
        Test that a talent is not duplicated when added to two different pools in two different steps.
        """
        with Form(self.env["talent.pool.add.applicants"]) as wizard:
            wizard.talent_pool_ids = self.t_talent_pool_1
            wizard.applicant_ids = self.t_applicant_1
        tp_applicant_1 = wizard.record._add_applicants_to_pool()

        self.assertTrue(tp_applicant_1, "An applicant('talent') should be created when adding an applicant to a pool")
        self.assertEqual(
            len(tp_applicant_1), 1, "Exactly one 'talent' should be created when adding an applicant to a pool"
        )

        # Try adding the same applicant to a different pool
        # This is impossible through the UI as there is a domain on the
        # `applicant_ids` field.
        wizard = Form(self.env["talent.pool.add.applicants"])
        wizard.talent_pool_ids = self.t_talent_pool_2
        wizard.applicant_ids = self.t_applicant_1
        tp_applicant_2 = wizard.save()._add_applicants_to_pool()
        self.assertFalse(tp_applicant_2, "A second talent for the same applicant should not have been created")

        wizard = Form(self.env["talent.pool.add.applicants"])
        wizard.talent_pool_ids = self.t_talent_pool_2
        wizard.applicant_ids = tp_applicant_1
        tp_applicant_2 = wizard.save()._add_applicants_to_pool()

        self.assertEqual(tp_applicant_1, tp_applicant_2, "tp_applicant_1 and tp_applicant_2 should be the same record")
        self.assertEqual(
            tp_applicant_1.talent_pool_ids,
            self.t_talent_pool_1 | self.t_talent_pool_2,
            f"tp_applicant_1 should be linked to {self.t_talent_pool_1.name} and {self.t_talent_pool_2.name}",
        )

    def test_tags_are_added_to_talent(self):
        """
        Test that a tag is added to the talent but not the applicant when creating talents.
        """
        tag = self.env["hr.applicant.category"].create({"name": "Test Tag"})

        talent_pool_applicant = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant_1,
                    "talent_pool_ids": self.t_talent_pool_1,
                    "categ_ids": tag,
                }
            )
            ._add_applicants_to_pool()
        )
        self.assertTrue(talent_pool_applicant, "A 'talent' should have been created")
        self.assertFalse(self.t_applicant_1.categ_ids, "The original applicant should not have any linked tags")
        self.assertEqual(
            talent_pool_applicant.categ_ids, tag, "The 'talent' should have the tag 'Test Tag' linked to it"
        )

    def test_add_talent_to_one_job(self):
        """
        Test that a talent is duplicated when added to a job
        """
        pool_wizard = Form(self.env["talent.pool.add.applicants"])
        pool_wizard.talent_pool_ids = self.t_talent_pool_1
        pool_wizard.applicant_ids = self.t_applicant_1
        talent_pool_applicant = pool_wizard.save()._add_applicants_to_pool()

        recuritment_stage = self.env["hr.recruitment.stage"].create({
            "name": "Recruitment Stage",
            "job_ids": self.t_job_2.ids,
            "template_id": self.mail_template.id,
            "sequence": 0,
        })

        self.assertEqual(
            len(talent_pool_applicant), 1, "Exactly one 'talent' should be created when adding an applicant to a pool"
        )

        job_wizard = Form(
            self.env["job.add.applicants"].with_context({"default_applicant_ids": talent_pool_applicant.ids})
        )
        job_wizard.job_ids = self.t_job_2
        job_2_applicant = job_wizard.save()._add_applicants_to_job()
        self.flush_tracking()

        all_applications = self.env["hr.applicant"].search(Domain("partner_name", "=", "Test Applicant 1"))
        self.assertEqual(
            len(all_applications),
            3,
            """There should be three applications with the name 'Test Applicant 1' - The original, the talent and the one created through the job.add.applicants wizard""",
        )
        self.assertEqual(
            job_2_applicant,
            self.t_job_2.application_ids,
            "Job_2_applicant, created through the wizard, should be linked to Job 2",
        )
        self.assertNotEqual(
            job_2_applicant, talent_pool_applicant, "Job_2_applicant and the talent should not be the same record"
        )

        # Make sure that the stage was populated correctly during creation not in compute,
        # If it was passed in creation the record will have the mail linked to the stage
        self.assertEqual(job_2_applicant.stage_id, recuritment_stage)
        self.assertEqual(job_2_applicant.message_ids[0].subject, self.mail_template.subject)

    def test_add_talent_to_multiple_jobs(self):
        """
        Test that a talent is duplicated multiple times when added to multiple jobs.
        """
        pool_wizard = Form(self.env["talent.pool.add.applicants"])
        pool_wizard.talent_pool_ids = self.t_talent_pool_1
        pool_wizard.applicant_ids = self.t_applicant_1
        pool_wizard.save().action_add_applicants_to_pool()

        talent_pool_applicant = self.t_talent_pool_1.talent_ids
        self.assertEqual(
            len(talent_pool_applicant), 1, "Exactly one 'talent' should be created when adding an applicant to a pool"
        )

        job_wizard = Form(
            self.env["job.add.applicants"].with_context({"default_applicant_ids": talent_pool_applicant.ids})
        )
        job_wizard.job_ids.add(self.t_job_2)
        job_wizard.job_ids.add(self.t_job_3)
        new_job_applicants = job_wizard.save()._add_applicants_to_job()

        all_applications = self.env["hr.applicant"].search(Domain("partner_name", "=", "Test Applicant 1"))
        self.assertEqual(
            len(all_applications),
            4,
            """There should be four applications with the name 'Test Applicant' - The original, the talent and one each for job_2 and job_3, created through the wizard""",
        )
        self.assertEqual(
            new_job_applicants.job_id,
            self.t_job_2 | self.t_job_3,
            "new_job_applicants, created through the wizard, should be linked to Job 2 and Job 3",
        )

    def test_add_multiple_talents_to_multiple_jobs(self):
        """
        Test that multiple talents are duplicated multiple times when added to multiple jobs.
        """
        pool_wizard = Form(self.env["talent.pool.add.applicants"])
        pool_wizard.talent_pool_ids = self.t_talent_pool_1
        pool_wizard.applicant_ids.add(self.t_applicant_1)
        pool_wizard.applicant_ids.add(self.t_applicant_2)
        talent_pool_applicants = pool_wizard.save()._add_applicants_to_pool()
        self.assertEqual(
            len(talent_pool_applicants), 2, "Exactly two 'talents' should be created when adding an applicant to a pool"
        )

        job_wizard = Form(
            self.env["job.add.applicants"].with_context({"default_applicant_ids": talent_pool_applicants.ids})
        )
        job_wizard.job_ids.add(self.t_job_2)
        job_wizard.job_ids.add(self.t_job_3)
        new_job_applicants = job_wizard.save()._add_applicants_to_job()

        all_a_1_applications = self.env["hr.applicant"].search(Domain("partner_name", "=", "Test Applicant 1"))
        all_a_2_applications = self.env["hr.applicant"].search(Domain("partner_name", "=", "Test Applicant 2"))
        self.assertEqual(
            len(all_a_1_applications),
            4,
            """There should be four applications with the name 'Test Applicant 1' - The original, the talent and one each for job_2 and job_3, created through the wizard""",
        )
        self.assertEqual(
            len(all_a_2_applications),
            4,
            """There should be four applications with the name 'Test Applicant 2' - The original, the talent and one each for job_2 and job_3, created through the wizard""",
        )
        new_job_applicants = new_job_applicants.mapped(lambda a: {"name": a.partner_name, "job": a.job_id})
        expected = [
            {"name": "Test Applicant 1", "job": self.t_job_2},
            {"name": "Test Applicant 1", "job": self.t_job_3},
            {"name": "Test Applicant 2", "job": self.t_job_2},
            {"name": "Test Applicant 2", "job": self.t_job_3},
        ]
        self.assertEqual(
            new_job_applicants,
            expected,
            "new_job_applicants, created through the wizard, should be linked to Job 2 and Job 3",
        )

    def test_update_applicant_after_adding_to_pool(self):
        """
        Test that an applicant's fields (e.g., email) can still be updated after adding them to a talent pool.
        """
        self.env["talent.pool.add.applicants"].create({
            "applicant_ids": self.t_applicant_1.ids,
        }).action_add_applicants_to_pool()

        new_email = "updated@gmail.com"
        self.t_applicant_1.write({"email_from": new_email})
        self.assertEqual(
            self.t_applicant_1.email_from,
            new_email,
            "The email_from field should be updated successfully",
        )

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env.flush_all()
        self.cr.flush()
