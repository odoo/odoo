import ast
import base64

from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tests import Form, TransactionCase, tagged


@tagged("recruitment")
class TestRecruitment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env["res.company"].create(
            {
                "name": "Company Test",
                "country_id": cls.env.ref("base.us").id,
            }
        )
        cls.env.user.company_id = cls.company
        cls.env.user.company_ids = [Command.set(cls.company.ids)]

        cls.TEXT = base64.b64encode(bytes("hr_recruitment", "utf-8"))
        cls.Attachment = cls.env["ir.attachment"]

    def test_infer_applicant_lang_from_context(self):
        self.env["res.lang"]._activate_lang("pl_PL")
        self.env["res.lang"]._activate_lang("en_US")
        self.env["ir.default"].set("res.partner", "lang", "en_US")

        applicant = (
            self.env["hr.applicant"]
            .sudo()
            .with_context(lang="pl_PL")
            .create(
                {
                    "partner_name": "Test Applicant",
                    "email_from": "test_aplicant@example.com",
                }
            )
        )
        self.assertEqual(
            applicant.partner_id.lang,
            "pl_PL",
            "Context langague not used for partner creation",
        )

    def test_duplicate_email(self):
        dup1, dup2, no_dup = self.env["hr.applicant"].create(
            [
                {
                    "partner_name": "Application 1",
                    "email_from": "laurie.poiret@aol.ru",
                },
                {
                    "partner_name": "Application 2",
                    "email_from": "laurie.POIRET@aol.ru",
                },
                {
                    "partner_name": "Application 3",
                    "email_from": "laure.poiret@aol.ru",
                },
            ]
        )
        self.assertEqual(dup1.application_count, 2)
        self.assertEqual(dup2.application_count, 2)
        self.assertEqual(no_dup.application_count, 1)

    def test_similar_applicants_count(self):
        A, B, C, D, E, F, _ = self.env["hr.applicant"].create(
            [
                {
                    "active": False,
                    "partner_name": "Application A",
                    "email_from": "abc@odoo.com",
                    "phone_ids": [Command.create({"number": "123", "type": "mobile"})],
                },
                {
                    "partner_name": "Application B",
                    "phone_ids": [Command.create({"number": "456", "type": "mobile"})],
                },
                {
                    "partner_name": "Application C",
                    "email_from": "def@odoo.com",
                    "phone_ids": [Command.create({"number": "123", "type": "mobile"})],
                },
                {
                    "partner_name": "Application D",
                    "email_from": "abc@odoo.com",
                    "phone_ids": [Command.create({"number": "456", "type": "mobile"})],
                },
                {
                    "partner_name": "Application E",
                    "phone_ids": [Command.create({"number": "", "type": "mobile"})],
                },
                {
                    "partner_name": "Application F",
                    "email_from": "ghi@odoo.com",
                    "phone_ids": [Command.create({"number": "789", "type": "mobile"})],
                },
                {
                    "partner_name": "Application G",
                },
            ]
        )
        self.assertEqual(A.application_count, 3)
        self.assertEqual(B.application_count, 2)
        self.assertEqual(C.application_count, 2)
        self.assertEqual(D.application_count, 3)
        self.assertEqual(E.application_count, 0)
        self.assertEqual(F.application_count, 1)

    def test_talent_pool_count(self):
        tp_A, tp_B = self.env["hr.talent.pool"].create(
            [{"name": "Cool Pool"}, {"name": "Other Pool"}]
        )
        t_A, t_B = self.env["hr.applicant"].create(
            [
                {
                    "partner_name": "Talent A",
                    "email_from": "abc@example.com",
                    "phone_ids": [Command.create({"number": "1234", "type": "mobile"})],
                    "linkedin_profile": "linkedin/talent",
                    "talent_pool_ids": [tp_A.id, tp_B.id],
                },
                {
                    "partner_name": "Talent B",
                    "email_from": "talent_b@example.com",
                    "phone_ids": [Command.create({"number": "9999", "type": "mobile"})],
                    "talent_pool_ids": [tp_B.id],
                },
            ]
        )
        t_A.pool_applicant_id = t_A.id
        t_B.pool_applicant_id = t_B.id

        A, B, C, D, E, F, G = self.env["hr.applicant"].create(
            [
                {"partner_name": "A", "pool_applicant_id": t_A.id},
                {
                    "partner_name": "B",
                    "email_from": "def@example.com",
                    "phone_ids": [Command.create({"number": "6789", "type": "mobile"})],
                    "linkedin_profile": "linkedin/b",
                    "pool_applicant_id": t_A.id,
                },
                {
                    "partner_name": "C",
                    "email_from": "def@example.com",
                },
                {
                    "partner_name": "D",
                    "phone_ids": [Command.create({"number": "6789", "type": "mobile"})],
                },
                {
                    "partner_name": "E",
                    "linkedin_profile": "linkedin/b",
                },
                {
                    "partner_name": "F",
                    "email_from": "not_linked@example.com",
                    "phone_ids": [
                        Command.create({"number": "00000", "type": "mobile"})
                    ],
                    "linkedin_profile": "linkedin/not_linked",
                },
                {"partner_name": "G", "pool_applicant_id": t_B.id},
            ]
        )
        self.assertEqual(t_A.talent_pool_count, 2)
        self.assertEqual(t_B.talent_pool_count, 1)
        self.assertEqual(A.talent_pool_count, 2)
        self.assertEqual(B.talent_pool_count, 2)
        self.assertEqual(C.talent_pool_count, 2)
        self.assertEqual(D.talent_pool_count, 2)
        self.assertEqual(E.talent_pool_count, 2)
        self.assertEqual(F.talent_pool_count, 0)
        self.assertEqual(G.talent_pool_count, 1)

    def test_compute_and_search_is_applicant_in_pool(self):
        talent_pool = self.env["hr.talent.pool"].create({"name": "Cool Pool"})
        job = self.env["hr.job"].create(
            {
                "name": "Cool Job",
            }
        )
        A, B, C, D, E, F, G, H = self.env["hr.applicant"].create(
            [
                {
                    "partner_name": "Talent A",
                    "email_from": "mainTalentEmail@example.com",
                    "talent_pool_ids": talent_pool.ids,
                },
                {
                    "partner_name": "Applicant 1 B",
                    "email_from": "otherTalentEmail@example.com",
                    "phone_ids": [Command.create({"number": "1234", "type": "mobile"})],
                    "linkedin_profile": "linkedin.com/in/applicant",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Applicant 1 C",
                    "email_from": "otherTalentEmail@example.com",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Applicant 1 D",
                    "phone_ids": [Command.create({"number": "1234", "type": "mobile"})],
                    "job_id": job.id,
                },
                {
                    "partner_name": "Applicant 1 E",
                    "linkedin_profile": "linkedin.com/in/applicant",
                    "job_id": job.id,
                },
                {
                    "partner_name": "A different applicant F",
                    "email_from": "differentEmail@example.com",
                    "phone_ids": [Command.create({"number": "9876", "type": "mobile"})],
                    "linkedin_profile": "linkedin.com/in/NotAnApplicant",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Talent With No information G",
                    "talent_pool_ids": talent_pool.ids,
                },
                {
                    "partner_name": "Applicant With No information H",
                },
            ]
        )
        B.pool_applicant_id = A.id
        H.pool_applicant_id = G.id

        self.assertTrue(A.is_applicant_in_pool)
        self.assertTrue(B.is_applicant_in_pool)
        self.assertTrue(C.is_applicant_in_pool)
        self.assertTrue(D.is_applicant_in_pool)
        self.assertTrue(E.is_applicant_in_pool)
        self.assertFalse(F.is_applicant_in_pool)
        self.assertTrue(G.is_applicant_in_pool)
        self.assertTrue(H.is_applicant_in_pool)

        applicant = self.env["hr.applicant"]
        in_pool_domain = applicant._search_is_applicant_in_pool("in", [True])
        in_pool_applicants = applicant.search(
            Domain.AND([in_pool_domain, [("company_id", "=", self.env.company.id)]])
        )
        out_of_pool_applicants = applicant.search(
            Domain.AND(
                [~Domain(in_pool_domain), [("company_id", "=", self.env.company.id)]]
            )
        )
        self.assertCountEqual(in_pool_applicants, A | B | C | D | E | G | H)
        self.assertCountEqual(out_of_pool_applicants, F)

    def test_application_no_partner_duplicate(self):
        applicant_data = {
            "partner_name": "Test",
            "email_from": "test@thisisatest.com",
        }
        self.env["hr.applicant"].create(applicant_data)
        partner_count = self.env["res.partner"].search_count(
            [("email", "=", "test@thisisatest.com")]
        )
        self.assertEqual(partner_count, 1)
        self.env["hr.applicant"].create(applicant_data)
        partner_count = self.env["res.partner"].search_count(
            [("email", "=", "test@thisisatest.com")]
        )
        self.assertEqual(partner_count, 1)

    def test_target_on_application_hiring(self):
        job = self.env["hr.job"].create(
            {
                "name": "Test Job",
                "no_of_recruitment": 1,
            }
        )
        applicant = self.env["hr.applicant"].create(
            {
                "partner_name": "Test Applicant",
                "job_id": job.id,
            }
        )
        stage_new = self.env["hr.recruitment.stage"].create(
            {
                "name": "New",
                "sequence": 0,
                "hired_stage": False,
            }
        )
        stage_hired = self.env["hr.recruitment.stage"].create(
            {
                "name": "Hired",
                "sequence": 1,
                "hired_stage": True,
            }
        )
        self.assertEqual(job.no_of_recruitment, 1)
        applicant.stage_id = stage_hired
        self.assertEqual(job.no_of_recruitment, 0)

        applicant.stage_id = stage_new
        self.assertEqual(job.no_of_recruitment, 1)

    def test_open_refuse_applicant_wizard_without_partner_name(self):
        applicant = self.env["hr.applicant"].create(
            {
                "phone_ids": [Command.create({"number": "123", "type": "mobile"})],
            }
        )
        wizard = Form(
            self.env["applicant.get.refuse.reason"].with_context(
                default_applicant_ids=[applicant.id], active_test=False
            )
        )

        wizard_applicant = wizard.applicant_ids[0]
        self.assertFalse(wizard_applicant.partner_name)

    def test_applicant_refuse_reason(self):

        refuse_reason = self.env["hr.applicant.refuse.reason"].create(
            [{"name": "Fired"}]
        )

        app_1, app_2 = self.env["hr.applicant"].create(
            [
                {
                    "partner_name": "Laurie Poiret",
                    "email_from": "laurie.poiret@aol.ru",
                },
                {
                    "partner_name": "Mitchell Admin",
                    "email_from": "mitchell_admin@example.com",
                },
            ]
        )

        applicant_get_refuse_reason = self.env["applicant.get.refuse.reason"].create(
            [
                {
                    "refuse_reason_id": refuse_reason.id,
                    "applicant_ids": [app_1.id],
                    "duplicates": True,
                }
            ]
        )
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self.assertFalse(
            self.env["hr.applicant"].search(
                [("email_from", "ilike", "laurie.poiret@aol.ru")]
            )
        )
        self.assertEqual(
            self.env["hr.applicant"].search(
                [("email_from", "ilike", "mitchell_admin@example.com")]
            ),
            app_2,
        )

    def test_applicant_refuse_mail_from_template(self):
        mail_template = self.env["mail.template"].create(
            {
                "name": "Test template",
                "model_id": self.env["ir.model"]._get("hr.applicant").id,
                "email_from": "test@test.test",
            }
        )
        refuse_reason = self.env["hr.applicant.refuse.reason"].create(
            {
                "name": "Not good",
            }
        )
        applicant = self.env["hr.applicant"].create(
            {
                "partner_name": "Laurie Poiret",
                "email_from": "laurie.poiret@aol.ru",
            }
        )
        applicant_get_refuse_reason = self.env["applicant.get.refuse.reason"].create(
            [
                {
                    "refuse_reason_id": refuse_reason.id,
                    "applicant_ids": applicant.ids,
                    "duplicates": True,
                }
            ]
        )
        mail_values = applicant_get_refuse_reason._prepare_mail_values(applicant)
        self.assertEqual(mail_values["email_from"], self.env.user.email_formatted)

        refuse_reason_template = self.env["hr.applicant.refuse.reason"].create(
            {
                "name": "Fired",
                "template_id": mail_template.id,
            }
        )
        applicant_get_refuse_reason.refuse_reason_id = refuse_reason_template
        mail_values = applicant_get_refuse_reason._prepare_mail_values(applicant)
        self.assertEqual(mail_values["email_from"], "test@test.test")

    def test_copy_attachments_while_creating_employee(self):
        applicant_1 = self.env["hr.applicant"].create(
            {"partner_name": "Applicant 1", "email_from": "test_applicant@example.com"}
        )
        applicant_attachment = self.Attachment.create(
            {
                "datas": self.TEXT,
                "name": "textFile.txt",
                "mimetype": "text/plain",
                "res_model": applicant_1._name,
                "res_id": applicant_1.id,
            }
        )

        employee_applicant = applicant_1.create_employee_from_applicant()
        self.assertTrue(employee_applicant["res_id"])
        attachment_employee_applicant = self.Attachment.search(
            [
                ("res_model", "=", employee_applicant["res_model"]),
                ("res_id", "=", employee_applicant["res_id"]),
            ]
        )
        self.assertEqual(
            applicant_attachment["datas"], attachment_employee_applicant["datas"]
        )

    def test_other_applications_count(self):
        A1, A2, A3 = self.env["hr.applicant"].create(
            [
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
            ]
        )

        self.assertEqual(A1.application_count, 3)

        A2.action_archive()
        self.assertEqual(
            A1.application_count,
            3,
            "Application_count should not change when archiving a linked application",
        )
        refuse_reason = self.env["hr.applicant.refuse.reason"].create(
            [{"name": "Fired"}]
        )
        applicant_get_refuse_reason = self.env["applicant.get.refuse.reason"].create(
            [
                {
                    "refuse_reason_id": refuse_reason.id,
                    "applicant_ids": [A3.id],
                }
            ]
        )
        applicant_get_refuse_reason.action_refuse_reason_apply()
        self.assertEqual(
            A1.application_count,
            3,
            "The other_applications_count should not change when refusing an application",
        )

    def test_open_other_applications_count(self):
        A1, _, _ = self.env["hr.applicant"].create(
            [
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
                {"partner_name": "test", "email_from": "test@example.com"},
            ]
        )

        res = A1.action_view_applications()
        self.assertEqual(
            len(res["domain"][0][2]), 3, "The list view should display 3 applications"
        )

    def test_applicant_modify_email_number(self):
        applicant = self.env["hr.applicant"].create(
            {
                "partner_name": "Mary Applicant",
                "email_from": "applicant@example.com",
                "phone_ids": [
                    Command.create({"number": "123456789", "type": "mobile"})
                ],
            }
        )
        self.assertEqual(
            applicant.partner_id.email,
            "applicant@example.com",
            "Email should have been set on the partner.",
        )
        self.assertEqual(
            applicant.partner_id.phone_ids._primary().number,
            "123456789",
            "Phone should have been set on the partner.",
        )

        applicant.email_from = "applicant_diff@example.com"
        self.assertEqual(
            applicant.partner_id.email,
            "applicant_diff@example.com",
            "Email should have been updated on the partner.",
        )
        applicant._phone_replace_number("phone_ids", "987654321")
        self.assertEqual(
            applicant.partner_id.phone_ids._primary().number,
            "987654321",
            "Phone should have been updated on the partner.",
        )

    def test_application_status_search_agrees_with_compute(self):
        Applicant = self.env["hr.applicant"].with_context(active_test=False)
        refuse_reason = self.env["hr.applicant.refuse.reason"].create({"name": "R"})
        refused_archived, refused_active, archived, hired, ongoing = Applicant.create(
            [
                {"partner_name": "refused archived", "active": False},
                {"partner_name": "refused active"},
                {"partner_name": "archived", "active": False},
                {"partner_name": "hired", "date_closed": "2026-01-01 00:00:00"},
                {"partner_name": "ongoing"},
            ]
        )
        (refused_archived | refused_active).refuse_reason_id = refuse_reason
        expected = {
            refused_archived: "refused",
            refused_active: "refused",
            archived: "archived",
            hired: "hired",
            ongoing: "ongoing",
        }
        for applicant, status in expected.items():
            self.assertEqual(applicant.application_status, status)
        all_ids = list(expected)
        for status in ("refused", "archived", "hired", "ongoing"):
            found = Applicant.search(
                [
                    ("application_status", "=", status),
                    ("id", "in", [a.id for a in all_ids]),
                ]
            )
            self.assertEqual(
                set(found.ids),
                {a.id for a, s in expected.items() if s == status},
                f"search for {status} must return exactly the applicants computing to it",
            )

    def test_job_platform_without_regex_keeps_sender_name(self):
        self.env["hr.job.platform"].create(
            {"name": "Plain Platform", "email": "plain@platform.com"}
        )
        applicant = self.env["hr.applicant"].message_new(
            {
                "message_id": "plain-platform",
                "email_from": '"Jane Roe" <plain@platform.com>',
                "from": '"Jane Roe" <plain@platform.com>',
                "subject": "Application received",
                "body": None,
            }
        )
        self.assertEqual(applicant.partner_name, "Jane Roe")
        self.assertFalse(applicant.email_from)

    def test_first_stage_is_shared_and_prefers_job_specific_stage(self):
        Stage = self.env["hr.recruitment.stage"]
        job = self.env["hr.job"].create({"name": "Tie Job"})
        Stage.search([]).write({"sequence": 10})
        folded = Stage.create({"name": "Folded", "sequence": 0, "fold": True})
        generic = Stage.create({"name": "Generic", "sequence": 1})
        specific = Stage.create({"name": "Specific", "sequence": 1, "job_ids": job.ids})
        first = Stage._get_first_stage_by_job(job)[job]
        self.assertEqual(first, specific)
        self.assertNotEqual(first, folded)
        self.assertEqual(job._get_first_stage(), specific)
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Tie", "job_id": job.id}
        )
        self.assertEqual(applicant.stage_id, specific)
        applicant.write({"stage_id": generic.id, "active": False})
        applicant.action_unarchive()
        self.assertEqual(applicant.stage_id, specific)
        self.assertEqual(applicant.last_stage_id, generic)

    def test_batch_hiring_updates_recruitment_target_once_per_job(self):
        job = self.env["hr.job"].create({"name": "Batch Job", "no_of_recruitment": 3})
        applicants = self.env["hr.applicant"].create(
            [{"partner_name": f"A{i}", "job_id": job.id} for i in range(2)]
        )
        new_stage = applicants.stage_id
        hired = self.env["hr.recruitment.stage"].create(
            {"name": "Hired", "sequence": 50, "hired_stage": True}
        )
        applicants.write({"stage_id": hired.id})
        self.assertEqual(job.no_of_recruitment, 1)
        self.assertEqual(applicants.mapped("last_stage_id"), new_stage)
        self.assertTrue(all(applicants.mapped("date_closed")))
        applicants.write({"stage_id": new_stage.id})
        self.assertEqual(job.no_of_recruitment, 3)
        self.assertFalse(any(applicants.mapped("date_closed")))
        applicants.write({"stage_id": hired.id})
        applicants.write({"stage_id": hired.id})
        self.assertEqual(job.no_of_recruitment, 1)

    def test_refuse_wizard_computes_duplicates_per_wizard(self):
        a1, a2, b1 = self.env["hr.applicant"].create(
            [
                {"partner_name": "A", "email_from": "a@dup.com"},
                {"partner_name": "A", "email_from": "a@dup.com"},
                {"partner_name": "B", "email_from": "b@dup.com"},
            ]
        )
        reason = self.env["hr.applicant.refuse.reason"].create({"name": "R"})
        wizard_a, wizard_b = self.env["applicant.get.refuse.reason"].create(
            [
                {
                    "refuse_reason_id": reason.id,
                    "applicant_ids": a1.ids,
                    "duplicates": True,
                },
                {
                    "refuse_reason_id": reason.id,
                    "applicant_ids": b1.ids,
                    "duplicates": True,
                },
            ]
        )
        self.assertEqual(wizard_a.duplicates_count, 1)
        self.assertEqual(wizard_a.duplicate_applicant_ids, a2)
        self.assertEqual(wizard_b.duplicates_count, 0)
        self.assertFalse(wizard_b.duplicate_applicant_ids)

    def test_employee_from_applicant_gets_job_and_department(self):
        department = self.env["hr.department"].create(
            {"name": "Dept", "company_id": self.company.id}
        )
        job = self.env["hr.job"].create(
            {
                "name": "Job",
                "department_id": department.id,
                "company_id": self.company.id,
            }
        )
        applicant = self.env["hr.applicant"].create(
            {
                "partner_name": "Newbie",
                "email_from": "newbie@example.com",
                "job_id": job.id,
            }
        )
        action = applicant.create_employee_from_applicant()
        employee = self.env["hr.employee"].browse(action["res_id"])
        self.assertEqual(employee.job_id, job)
        self.assertEqual(employee.department_id, department)
        self.assertEqual(employee.job_title, job.name)
        self.assertEqual(employee.partner_id, applicant.partner_id)
        self.assertEqual(employee.applicant_ids, applicant)

    def test_job_activity_count_counts_my_activities_on_open_applicants(self):
        job = self.env["hr.job"].create({"name": "Counted Job"})
        hired = self.env["hr.recruitment.stage"].create(
            {"name": "Hired", "sequence": 60, "hired_stage": True}
        )
        open_applicant, hired_applicant, archived_applicant = self.env[
            "hr.applicant"
        ].create(
            [
                {"partner_name": "Open", "job_id": job.id},
                {"partner_name": "Hired", "job_id": job.id, "stage_id": hired.id},
                {"partner_name": "Archived", "job_id": job.id, "active": False},
            ]
        )
        other_user = self.env["res.users"].create(
            {
                "name": "Other",
                "login": "other-recruiter@example.com",
                "group_ids": [
                    Command.link(
                        self.env.ref("hr_recruitment.group_hr_recruitment_user").id
                    )
                ],
            }
        )
        for applicant, user in (
            (open_applicant, self.env.user),
            (open_applicant, self.env.user),
            (open_applicant, other_user),
            (hired_applicant, self.env.user),
            (archived_applicant, self.env.user),
        ):
            applicant.activity_schedule("mail.mail_activity_data_todo", user_id=user.id)
        self.assertEqual(job.activity_count, 2)
        self.assertEqual(job.with_user(other_user).activity_count, 1)

    def test_refusing_an_application_of_a_talent_refuses_its_siblings(self):
        """Driven through the module's own wizards, no field set by hand.

        Pool an applicant, put that talent on a second job, then correct the
        e-mail on the first application: ``write`` propagates the correction to
        the talent but not to the sibling application, so the sibling now shares
        only ``pool_applicant_id`` with the refused one. The wizard offers it as
        a duplicate and used to have no original to point it at -- a KeyError on
        an ordinary refusal.
        """
        job_one, job_two = self.env["hr.job"].create(
            [{"name": "First Job"}, {"name": "Second Job"}]
        )
        pool = self.env["hr.talent.pool"].create({"name": "Pool"})
        application = self.env["hr.applicant"].create(
            {
                "partner_name": "Rita Flow",
                "email_from": "rita@example.com",
                "job_id": job_one.id,
            }
        )
        self.env.flush_all()

        self.env["talent.pool.add.applicants"].create(
            {
                "applicant_ids": [Command.set(application.ids)],
                "talent_pool_ids": [Command.set(pool.ids)],
            }
        ).action_add_applicants_to_pool()
        self.env.flush_all()
        talent = application.pool_applicant_id
        self.assertTrue(talent)

        self.env["job.add.applicants"].create(
            {
                "applicant_ids": [Command.set(talent.ids)],
                "job_ids": [Command.set(job_two.ids)],
            }
        ).action_add_applicants_to_job()
        self.env.flush_all()
        sibling = self.env["hr.applicant"].search([("job_id", "=", job_two.id)])
        self.assertEqual(sibling.pool_applicant_id, talent)

        application.write({"email_from": "rita.flow@example.com"})
        self.env.flush_all()
        self.assertEqual(talent.email_from, "rita.flow@example.com")
        self.assertEqual(sibling.email_from, "rita@example.com")

        wizard = self.env["applicant.get.refuse.reason"].create(
            {
                "applicant_ids": [Command.set(application.ids)],
                "refuse_reason_id": self.env["hr.applicant.refuse.reason"]
                .search([], limit=1)
                .id,
                "duplicates": True,
            }
        )
        wizard.send_mail = False
        self.assertIn(sibling, wizard.duplicate_applicant_ids)
        self.assertEqual(
            wizard._get_related_original_applicants()[sibling], application
        )

        wizard.action_refuse_reason_apply()

        self.assertFalse(sibling.active)
        self.assertFalse(talent.active)

    def test_refusing_a_hand_picked_non_duplicate_does_not_crash(self):
        """``duplicate_applicant_ids`` is editable, so an unmatched entry is
        reachable and must degrade to a link-less log, not an exception."""
        job = self.env["hr.job"].create({"name": "Job"})
        original, real_duplicate, unrelated = self.env["hr.applicant"].create(
            [
                {
                    "partner_name": "Original",
                    "email_from": "same@example.com",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Duplicate",
                    "email_from": "same@example.com",
                    "job_id": job.id,
                },
                {
                    "partner_name": "Unrelated",
                    "email_from": "other@example.com",
                    "job_id": job.id,
                },
            ]
        )
        wizard = self.env["applicant.get.refuse.reason"].create(
            {
                "applicant_ids": [Command.set(original.ids)],
                "refuse_reason_id": self.env["hr.applicant.refuse.reason"]
                .search([], limit=1)
                .id,
                "duplicates": True,
            }
        )
        wizard.send_mail = False
        self.assertEqual(wizard.duplicate_applicant_ids, real_duplicate)
        wizard.duplicate_applicant_ids = [Command.link(unrelated.id)]
        self.assertEqual(wizard.duplicate_applicant_ids, real_duplicate + unrelated)

        wizard.action_refuse_reason_apply()

        self.assertFalse(real_duplicate.active)
        self.assertFalse(unrelated.active)
        self.assertNotIn(unrelated, wizard._get_related_original_applicants())

    def test_phone_reaches_the_contact_without_an_email(self):
        """The inverse is shared by ``email_from`` and ``phone_ids``: gating it
        on the e-mail dropped every phone edit on an e-mail-less applicant."""
        partner = self.env["res.partner"].create({"name": "Phone Only"})
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Phone Only", "partner_id": partner.id}
        )
        phone = self.env["phone.number"].create({"number": "+32470123456"})

        applicant.phone_ids = [Command.set(phone.ids)]
        self.env.flush_all()

        self.assertEqual(partner.phone_ids, phone)

    def test_a_phone_edit_does_not_rename_the_contact(self):
        """The phone sync must not drag the name sync onto a path it was never on:
        ``partner_id`` has no domain, so it can be a contact the recruiter picked."""
        contact = self.env["res.partner"].create(
            {"name": "ACME Corp", "is_company": True}
        )
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant One", "partner_id": contact.id}
        )
        phone = self.env["phone.number"].create({"number": "+32470999888"})

        applicant.phone_ids = [Command.set(phone.ids)]
        self.env.flush_all()

        self.assertEqual(contact.phone_ids, phone)
        self.assertEqual(contact.name, "ACME Corp")

    def test_rewriting_the_same_stage_keeps_the_previous_stage(self):
        """``last_stage_id`` answers "where did it come from"; a write that
        moves nothing must not answer "from where it already is"."""
        job = self.env["hr.job"].create({"name": "Job"})
        first, second = self.env["hr.recruitment.stage"].create(
            [
                {"name": "First", "sequence": 1},
                {"name": "Second", "sequence": 2},
            ]
        )
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant", "job_id": job.id, "stage_id": first.id}
        )
        applicant.write({"stage_id": second.id})
        self.assertEqual(applicant.last_stage_id, first)
        stamp = applicant.date_last_stage_update

        applicant.write({"stage_id": second.id})

        self.assertEqual(applicant.last_stage_id, first)
        self.assertEqual(applicant.date_last_stage_update, stamp)

    def test_unarchiving_clears_the_refusal_date(self):
        job = self.env["hr.job"].create({"name": "Job"})
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant", "job_id": job.id}
        )
        wizard = self.env["applicant.get.refuse.reason"].create(
            {
                "applicant_ids": [Command.set(applicant.ids)],
                "refuse_reason_id": self.env["hr.applicant.refuse.reason"]
                .search([], limit=1)
                .id,
            }
        )
        wizard.send_mail = False
        wizard.action_refuse_reason_apply()
        self.assertTrue(applicant.refuse_date)

        applicant.action_unarchive()

        self.assertFalse(applicant.refuse_reason_id)
        self.assertFalse(applicant.refuse_date)
        self.assertEqual(applicant.application_status, "ongoing")

    def test_stage_duration_of_a_refused_application_is_never_negative(self):
        """The refusal freezes the stage clock; it must not run it backwards."""
        job = self.env["hr.job"].create({"name": "Job"})
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant", "job_id": job.id}
        )
        self.env.flush_all()
        applicant.write(
            {
                "refuse_reason_id": self.env["hr.applicant.refuse.reason"]
                .search([], limit=1)
                .id,
                "active": False,
                "refuse_date": self.env.cr.now() - relativedelta(days=30),
            }
        )
        self.env.flush_all()
        applicant.invalidate_recordset()

        self.assertTrue(
            all(duration >= 0 for duration in applicant.duration_tracking.values()),
            applicant.duration_tracking,
        )

    def test_talent_pool_count_unions_every_matching_key(self):
        """An applicant can match one talent by e-mail and another by phone.

        The count used to report whichever key was checked first, so a person
        present in two pools through two talents read as being in one.
        """
        pool_a, pool_b = self.env["hr.talent.pool"].create(
            [{"name": "Pool A"}, {"name": "Pool B"}]
        )
        phone = self.env["phone.number"].create({"number": "+32470000111"})
        self.env["hr.applicant"].create(
            {
                "partner_name": "Matched by mail",
                "email_from": "shared@example.com",
                "talent_pool_ids": [Command.set(pool_a.ids)],
            }
        )
        self.env["hr.applicant"].create(
            {
                "partner_name": "Matched by phone",
                "phone_ids": [Command.set(phone.ids)],
                "talent_pool_ids": [Command.set(pool_b.ids)],
            }
        )
        self.env.flush_all()
        applicant = self.env["hr.applicant"].create(
            {
                "partner_name": "Both",
                "email_from": "shared@example.com",
                "phone_ids": [Command.set(phone.ids)],
            }
        )
        self.env.flush_all()
        applicant.invalidate_recordset()

        self.assertTrue(applicant.is_applicant_in_pool)
        self.assertEqual(applicant.talent_pool_count, 2)

    def test_the_scenario_is_detected_by_its_xml_id(self):
        Job = self.env["hr.job"]
        self.assertFalse(Job.is_recruitment_scenario_loaded())

        Job._action_load_recruitment_scenario()

        self.assertTrue(Job.is_recruitment_scenario_loaded())

    def test_a_new_job_is_a_favorite_of_its_creator(self):
        """``_default_favorite_user_ids`` used to be dead: ``create`` forced the
        key to ``[]`` before ``super()``, so the default never applied.

        Driven as a real user: ``self.env.user`` is ``__system__``, which is
        archived, and an archived user is filtered out of the m2m on read.
        """
        recruiter = self.env["res.users"].create(
            {
                "name": "Recruiter",
                "login": "favorite_recruiter",
                "group_ids": [
                    Command.link(
                        self.env.ref("hr_recruitment.group_hr_recruitment_manager").id
                    )
                ],
            }
        )
        job = self.env["hr.job"].with_user(recruiter).create({"name": "Job"})
        self.assertEqual(job.sudo().favorite_user_ids, recruiter)
        self.assertTrue(job.with_user(recruiter).is_user_favorite)

    def test_a_job_created_with_explicit_favorites_keeps_them(self):
        other = self.env["res.users"].create(
            {"name": "Other", "login": "other_favorite"}
        )
        job = self.env["hr.job"].create(
            {"name": "Job", "favorite_user_ids": [Command.set(other.ids)]}
        )
        self.assertEqual(job.favorite_user_ids, other)

    def test_restoring_a_job_restores_the_applications_it_archived(self):
        """The cascade was one-way: archiving a job archived every running
        application and un-archiving it restored none, with no record of which
        ones the cascade had taken."""
        job = self.env["hr.job"].create({"name": "Job"})
        running = self.env["hr.applicant"].create(
            [{"partner_name": f"Running {i}", "job_id": job.id} for i in range(3)]
        )
        refused = self.env["hr.applicant"].create(
            {"partner_name": "Refused", "job_id": job.id}
        )
        wizard = self.env["applicant.get.refuse.reason"].create(
            {
                "applicant_ids": [Command.set(refused.ids)],
                "refuse_reason_id": self.env["hr.applicant.refuse.reason"]
                .search([], limit=1)
                .id,
            }
        )
        wizard.send_mail = False
        wizard.action_refuse_reason_apply()
        self.env.flush_all()

        job.active = False
        self.env.flush_all()
        self.assertEqual(running.mapped("active"), [False] * 3)
        self.assertTrue(all(running.mapped("archived_with_job")))
        self.assertFalse(refused.archived_with_job)

        job.active = True
        self.env.flush_all()

        self.assertEqual(running.mapped("active"), [True] * 3)
        self.assertFalse(any(running.mapped("archived_with_job")))
        self.assertFalse(refused.active, "a refusal is not undone by restoring the job")
        self.assertTrue(refused.refuse_reason_id)

    def test_a_meeting_carries_the_cv_whichever_way_it_was_made(self):
        job = self.env["hr.job"].create({"name": "Job"})
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant", "job_id": job.id}
        )
        self.Attachment.create(
            {
                "name": "cv.txt",
                "datas": self.TEXT,
                "res_model": "hr.applicant",
                "res_id": applicant.id,
            }
        )
        self.env.flush_all()

        event = self.env["calendar.event"].create(
            {
                "name": "Interview",
                "applicant_id": applicant.id,
                "start": "2026-09-15 10:00:00",
                "stop": "2026-09-15 11:00:00",
            }
        )

        copied = self.Attachment.search(
            [("res_model", "=", "calendar.event"), ("res_id", "=", event.id)]
        )
        self.assertEqual(copied.name, "cv.txt")

    def test_recurring_interviews_do_not_each_copy_the_cv(self):
        """`_apply_recurrence` copies the base event's values, applicant included,
        so keying the copy on the record alone would duplicate every CV."""
        job = self.env["hr.job"].create({"name": "Job"})
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant", "job_id": job.id}
        )
        self.Attachment.create(
            {
                "name": "cv.txt",
                "datas": self.TEXT,
                "res_model": "hr.applicant",
                "res_id": applicant.id,
            }
        )
        self.env.flush_all()

        self.env["calendar.event"].create(
            {
                "name": "Daily interview",
                "applicant_id": applicant.id,
                "start": "2026-09-15 10:00:00",
                "stop": "2026-09-15 11:00:00",
                "recurrency": True,
                "repeat_unit": "day",
                "repeat_type": "count",
                "repeat_number": 4,
                "event_tz": "UTC",
            }
        )
        self.env.flush_all()

        copied = self.Attachment.search(
            [("res_model", "=", "calendar.event"), ("name", "=", "cv.txt")]
        )
        self.assertEqual(
            len(copied), 1, "the CV belongs on the meeting, not on every occurrence"
        )

    def test_an_emailed_application_takes_the_contact_number_not_its_address(self):
        contact = self.env["res.partner"].create(
            {
                "name": "Ada",
                "email": "ada.personal@example.com",
                "phone_ids": [Command.create({"number": "+32470112233"})],
            }
        )
        self.env.flush_all()

        applicant = self.env["hr.applicant"].message_new(
            {
                "from": "Ada <ada.work@example.com>",
                "author_id": contact.id,
                "subject": "Application",
                "body": "",
            }
        )

        self.assertEqual(applicant.phone_ids, contact.phone_ids)
        self.assertEqual(
            applicant.email_from,
            "Ada <ada.work@example.com>",
            "the address the applicant wrote from",
        )
        # This pins behaviour and does NOT discriminate the change it accompanies:
        # driven against the pre-audit code, which called
        # `_compute_partner_phone_email()` by hand here, it passes unchanged. That
        # compute does assign `email_from` from the contact, but the inverse has
        # already synced the contact to the applicant by then, so the assignment
        # is a no-op. Replacing the call was a clarity change, not a fix.

    def test_job_documents_span_the_job_and_its_unhired_applications(self):
        job, other_job = self.env["hr.job"].create([{"name": "A"}, {"name": "B"}])
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant", "job_id": job.id}
        )
        hired = self.env["hr.applicant"].create(
            {"partner_name": "Hired", "job_id": job.id}
        )
        hired.employee_id = self.env["hr.employee"].create({"name": "Hired"}).id
        for name, model, res_id in [
            ("on_job.txt", "hr.job", job.id),
            ("on_other_job.txt", "hr.job", other_job.id),
            ("on_applicant.txt", "hr.applicant", applicant.id),
            ("on_hired.txt", "hr.applicant", hired.id),
        ]:
            self.Attachment.create(
                {
                    "name": name,
                    "datas": self.TEXT,
                    "res_model": model,
                    "res_id": res_id,
                }
            )
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            sorted(job.document_ids.mapped("name")),
            ["on_applicant.txt", "on_job.txt"],
        )
        self.assertEqual(other_job.document_ids.mapped("name"), ["on_other_job.txt"])
        self.assertEqual(job.documents_count, 2)

    def test_degrees_come_back_in_the_order_they_were_dragged_into(self):
        """The degree list ships `widget="handle"`, which writes `sequence`.

        Without `_order` naming it the drag wrote a column nothing read, so the
        list re-rendered in id order and the reordering silently did nothing.
        """
        Degree = self.env["hr.recruitment.degree"]
        degrees = Degree.create(
            [
                {"name": "Third", "sequence": 30},
                {"name": "Second", "sequence": 20},
                {"name": "First", "sequence": 10},
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()

        found = Degree.search([("id", "in", degrees.ids)])

        self.assertEqual(found.mapped("name"), ["First", "Second", "Third"])

    def test_degrees_left_at_the_default_sequence_keep_a_stable_order(self):
        """Every row in an existing database sits at the default sequence, so the
        interesting case is the tie, not the reordering: a sort key with no
        tiebreak would order them however the plan happened to come out."""
        Degree = self.env["hr.recruitment.degree"]
        tied = Degree.create([{"name": f"Tied {index}"} for index in range(6)])
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(len(set(tied.mapped("sequence"))), 1, "the fixture must tie")

        orders = [Degree.search([("id", "in", tied.ids)]).ids for _ in range(4)]

        self.assertEqual(orders[0], sorted(tied.ids))
        self.assertTrue(all(order == orders[0] for order in orders))

    def test_the_status_filters_agree_with_the_status_field(self):
        """The search view hand-rolls the four `application_status` states.

        It has to: `application_status` is a computed field with a `search=`, and
        the ORM decides whether to apply `active_test` from the *raw* domain
        leaves, so `('application_status', '=', 'archived')` in a filter silently
        returns nothing. The duplication is therefore load-bearing, which makes
        it worth a test -- "Hired" used to be `date_closed != False` alone and
        listed applications that had been refused after reaching a hired stage,
        under both Hired and Refused at once.
        """
        job = self.env["hr.job"].create({"name": "Job"})
        hired_stage = self.env["hr.recruitment.stage"].create(
            {"name": "Contract Signed", "sequence": 99, "hired_stage": True}
        )
        reason = self.env["hr.applicant.refuse.reason"].search([], limit=1)

        def refuse(applicant):
            wizard = self.env["applicant.get.refuse.reason"].create(
                {
                    "applicant_ids": [Command.set(applicant.ids)],
                    "refuse_reason_id": reason.id,
                }
            )
            wizard.send_mail = False
            wizard.action_refuse_reason_apply()

        ongoing, hired, archived, refused, refused_after_hire = self.env[
            "hr.applicant"
        ].create([{"partner_name": name, "job_id": job.id} for name in "abcde"])
        hired.stage_id = hired_stage
        archived.action_archive()
        refuse(refused)
        refused_after_hire.stage_id = hired_stage
        refuse(refused_after_hire)
        everyone = ongoing | hired | archived | refused | refused_after_hire
        self.env.flush_all()
        self.env.invalidate_all()

        # read the domains off the view itself, so this fails if the view drifts
        arch = etree.fromstring(
            self.env.ref("hr_recruitment.hr_applicant_view_search_bis").arch
        )
        filters = {}
        for name in ("ongoing", "hired", "inactive", "refused"):
            [node] = arch.xpath(f"//filter[@name='{name}']")
            filters[name] = ast.literal_eval(node.get("domain"))

        for name, status in (
            ("ongoing", "ongoing"),
            ("hired", "hired"),
            ("inactive", "archived"),
            ("refused", "refused"),
        ):
            with self.subTest(filter=name):
                self.assertEqual(
                    self._named(everyone, filters[name]),
                    self._named(everyone, [("application_status", "=", status)]),
                    f"the {name!r} filter must select exactly the {status!r} status",
                )
        self.assertNotIn(
            refused_after_hire,
            self.env["hr.applicant"]
            .with_context(active_test=False)
            .search([("id", "in", everyone.ids), *filters["hired"]]),
            "a refused application is not a hire, whatever stage it reached",
        )

    def _named(self, population, domain):
        return set(
            self.env["hr.applicant"]
            .with_context(active_test=False)
            .search([("id", "in", population.ids), *domain])
            .mapped("partner_name")
        )

    def test_pooling_an_applicant_needs_no_elevated_rights(self):
        """The ordinary path runs on the recruiter's own rights."""
        recruiter = self._recruiter()
        pool = self.env["hr.talent.pool"].create({"name": "Pool"})
        applicant = self.env["hr.applicant"].create(
            {"partner_name": "Applicant", "email_from": "applicant@example.com"}
        )
        self.env.flush_all()

        wizard = (
            self.env["talent.pool.add.applicants"]
            .with_user(recruiter)
            .create(
                {
                    "applicant_ids": [Command.set(applicant.ids)],
                    "talent_pool_ids": [Command.set(pool.ids)],
                }
            )
        )
        wizard.action_add_applicants_to_pool()

        self.assertTrue(applicant.pool_applicant_id)
        self.assertEqual(applicant.pool_applicant_id.talent_pool_ids, pool)

    def test_pooling_cannot_write_to_a_talent_of_another_company(self):
        """`_add_applicants_to_pool` used to run entirely as superuser.

        An applicant the recruiter *can* see may carry a `pool_applicant_id`
        pointing at a talent in a company they cannot, and the elevation wrote to
        that talent -- putting a record the recruiter cannot read into a pool of
        their own company.
        """
        recruiter = self._recruiter()
        other_company = self.env["res.company"].create({"name": "Elsewhere"})
        foreign_pool = self.env["hr.talent.pool"].create(
            {"name": "Their pool", "company_id": other_company.id}
        )
        foreign_talent = self.env["hr.applicant"].create(
            {
                "partner_name": "Theirs",
                "email_from": "theirs@example.com",
                "company_id": other_company.id,
                "talent_pool_ids": [Command.set(foreign_pool.ids)],
            }
        )
        local = self.env["hr.applicant"].create(
            {
                "partner_name": "Ours",
                "email_from": "ours@example.com",
                "company_id": self.env.company.id,
                "pool_applicant_id": foreign_talent.id,
            }
        )
        our_pool = self.env["hr.talent.pool"].create(
            {"name": "Our pool", "company_id": self.env.company.id}
        )
        self.env.flush_all()
        self.assertFalse(
            self.env["hr.applicant"]
            .with_user(recruiter)
            .search([("id", "=", foreign_talent.id)]),
            "the fixture is pointless unless the talent is genuinely invisible",
        )

        wizard = (
            self.env["talent.pool.add.applicants"]
            .with_user(recruiter)
            .create(
                {
                    "applicant_ids": [Command.set(local.ids)],
                    "talent_pool_ids": [Command.set(our_pool.ids)],
                }
            )
        )
        # the write is buffered: the record rule is checked at flush, so a bare
        # `assertRaises` around the action alone exits before the error is raised
        # `assertRaises(AccessError)` cannot be used here, and the reason is
        # worth stating because the obvious test passes against the bug.
        # `TransactionCase._assertRaises` calls `cr.clear()` whenever the
        # expected exception is an `AccessError`, and that discards the state
        # staged before the block -- including this wizard's own `applicant_ids`,
        # which then reads empty. `_add_applicants_to_pool` iterates nothing, the
        # dangerous write never happens, and the assertion is vacuous. Measured:
        # with `cr.clear()` the foreign talent is untouched and no error is
        # raised; without it the error is raised every time, through either env.
        # So this asserts the property, which is the stronger claim anyway.
        refused = False
        try:
            wizard.action_add_applicants_to_pool()
            wizard.env.flush_all()
        except AccessError:
            refused = True
        foreign_talent.invalidate_recordset()

        self.assertTrue(refused, "a talent of another company must not be written")
        self.assertEqual(foreign_talent.talent_pool_ids, foreign_pool)

    def _recruiter(self):
        return self.env["res.users"].create(
            {
                "name": "Recruiter",
                "login": f"recruiter_{self.env.cr.now().timestamp()}",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "group_ids": [
                    Command.link(
                        self.env.ref("hr_recruitment.group_hr_recruitment_user").id
                    )
                ],
            }
        )
