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
