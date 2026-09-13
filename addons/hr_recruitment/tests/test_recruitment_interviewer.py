# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import new_test_user

from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged


@tagged('recruitment_interviewer')
class TestRecruitmentInterviewer(MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.simple_user = new_test_user(cls.env, 'smp',
            groups='base.group_user', name='Simple User', email='smp@example.com')
        cls.interviewer_user = new_test_user(cls.env, 'itw',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer', email='itw@example.com')
        cls.manager_user = new_test_user(cls.env, 'mng',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_manager',
            name='Recruitment Manager', email='mng@example.com')

        cls.job = cls.env['hr.job'].create({
            'name': 'super nice job',
            'user_id': cls.manager_user.id,
        })

    def test_interviewer_group(self):
        """
            Test that adding a user as interviewer to a job / applicant adds
            that user in the Interviewer group. Also checks that removing the
            user will remove them when they are no longer required (e.g. no
            longer interviewer of any job/applicant).
        """
        interviewer_group = self.env.ref('hr_recruitment.group_hr_recruitment_interviewer')

        self.assertFalse(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should not be interviewer")

        self.job.interviewer_ids = self.simple_user.ids
        self.assertTrue(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should be added as interviewer")

        self.job.write({'interviewer_ids': [(5, 0, 0)]})
        self.assertFalse(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should be removed from interviewer")

        applicant = self.env['hr.applicant'].create({
            'partner_name': 'toto',
            'job_id': self.job.id,
            'interviewer_ids': self.simple_user.ids,
        })
        self.assertTrue(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should be added as interviewer")

        applicant.interviewer_ids = False
        self.assertFalse(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should be removed from interviewer")

        self.job.interviewer_ids = self.simple_user.ids
        applicant.interviewer_ids = self.simple_user.ids
        self.assertTrue(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should be added as interviewer")

        applicant.interviewer_ids = False
        self.assertTrue(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should stay interviewer")

        self.job.write({'interviewer_ids': [(5, 0, 0)]})
        applicant.interviewer_ids = self.simple_user.ids
        self.assertTrue(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should stay interviewer")

        applicant.interviewer_ids = False
        self.assertFalse(interviewer_group.id in self.simple_user.all_group_ids.ids, "Simple User should be removed from interviewer")

    def test_interviewer_access_rights(self):
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'toto',
            'job_id': self.job.id,
        })

        with self.assertRaises(AccessError):
            applicant.with_user(self.interviewer_user).read()

        applicant = self.env['hr.applicant'].create({
            'partner_name': 'toto',
            'job_id': self.job.id,
            'interviewer_ids': self.interviewer_user.ids,
        })
        applicant.with_user(self.interviewer_user).read()

        self.job.interviewer_ids = self.interviewer_user.ids
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'toto',
            'job_id': self.job.id,
        })
        applicant.with_user(self.interviewer_user).read()

        # An interviewer can change the interviewers
        applicant.with_user(self.interviewer_user).interviewer_ids = self.simple_user.ids
        self.assertEqual(self.simple_user, applicant.interviewer_ids)

        with self.assertRaises(UserError):
            applicant.with_user(self.interviewer_user).create_employee_from_applicant()

    def test_refuse_mail_with_template_recipients(self):
        mail_template = self.env['mail.template'].create({
            'name': 'Test template',
            'model_id': self.env['ir.model']._get('hr.applicant').id,
            'email_from': 'from@test.test',
            'email_cc': 'cc@test.test',
            'email_to': '{{ object.partner_id.email }}',
            'partner_to': self.env.user.partner_id.id,
            'use_default_to': False,
            'subject': 'Application refused: {{ object.partner_name }}'
        })
        refuse_reason = self.env['hr.applicant.refuse.reason'].create({
            'name': 'Not good',
        })
        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Laurie Poiret',
            'email_from': 'laurie.poiret@aol.ru',
        })
        applicant_get_refuse_reason = self.env['applicant.get.refuse.reason'].create({
            'refuse_reason_id': refuse_reason.id,
            'applicant_ids': applicant.ids,
            'template_id': mail_template.id,
            'send_mail': True,
        })

        with self.mock_mail_gateway():
            applicant_get_refuse_reason.with_context(active_test=False).action_refuse_reason_apply()

        self.assertSentEmail(
            'from@test.test',
            [applicant.partner_id.email_formatted],
            subject='Application refused: Laurie Poiret',
        )
        partner_cc = self.env['res.partner'].search([('email', '=', 'cc@test.test')])
        self.assertTrue(partner_cc)
        self.assertSentEmail(
            'from@test.test',
            [partner_cc.email_formatted],
            subject='Application refused: Laurie Poiret',
        )

        # Restore applicant and set template to default
        applicant.action_unarchive()
        mail_template.email_from = False
        mail_template.use_default_to = True
        with self.mock_mail_gateway():
            applicant_get_refuse_reason.with_context(active_test=False).action_refuse_reason_apply()

        self.assertSentEmail(
            self.env.user.email_formatted,
            [applicant.partner_id.email_formatted],
            subject='Application refused: Laurie Poiret',
        )

    def test_update_interviewer_for_multiple_applicants(self):
        """
            Test that assigning interviewer to multiple applicants.
        """
        interviewer_user_1 = new_test_user(self.env, 'sma',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer1', email='sma@example.com')

        interviewer_user_2 = new_test_user(self.env, 'jab',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer2', email='jab@example.com')

        interviewer_user_3 = new_test_user(self.env, 'aad',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer3', email='aad@example.com')

        applicant = self.env['hr.applicant'].create({
            'partner_name': 'Applicant',
            'job_id': self.job.id,
            'interviewer_ids': [(6, 0, [interviewer_user_1.id])]
        })
        applicants = applicant + applicant.copy({'interviewer_ids': [(6, 0, [interviewer_user_2.id])]})

        # update interviewer to multiple applicants.
        applicants.write({'interviewer_ids': [(4, interviewer_user_3.id)]})

        # Ensure all interviewers are assigned
        self.assertCountEqual(
            applicants.interviewer_ids.ids, [interviewer_user_1.id, interviewer_user_2.id, interviewer_user_3.id]
        )

        # Checked that notification message is created
        message = self.env['mail.message'].search([('res_id', '=', applicant.id)], limit=1)
        self.assertEqual(message.subject, f"You have been assigned as an interviewer for {applicant.display_name}")

    def test_update_recruiter_for_ongoing_application(self):
        Application = self.env['hr.applicant']
        new_manager_user = new_test_user(self.env, 'thala',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_manager',
            name='New Recruitment Manager', email='thala@example.com')
        ongoing_application = Application.create({
            'job_id': self.job.id,
            'user_id': self.manager_user.id,
            'application_status': 'ongoing',
        })
        hired_application = Application.create({
            'job_id': self.job.id,
            'user_id': self.manager_user.id,
            'date_closed': fields.Datetime.now(),
            'application_status': 'hired',
        })
        self.job.write({'user_id': new_manager_user.id})
        self.assertEqual(ongoing_application.user_id, new_manager_user)
        self.assertEqual(hired_application.user_id, self.manager_user)
