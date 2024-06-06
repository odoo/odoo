# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import new_test_user, tagged, users


@tagged('post_install', '-at_install', 'utm_consistency')
class TestUTMConsistencyHrRecruitment(TestUTMCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_recruitment_source = cls.env['hr.recruitment.source'].create({
            'name': 'Recruitment Source'
        })

    @users('__system__')
    def test_utm_consistency(self):
        # the source is automatically created when creating a recruitment source
        utm_source = self.hr_recruitment_source.source_id

        with self.assertRaises(UserError):
            # can't unlink the source as it's used by a mailing.mailing as its source
            # unlinking the source would break all the mailing statistics
            utm_source.unlink()

        # you are not supposed to delete the 'utm_campaign_job' record as it is hardcoded in
        # the creation of the alias of the recruitment source
        with self.assertRaises(UserError):
            self.env.ref('hr_recruitment.utm_campaign_job').unlink()

    def test_create_alias(self):
        """This ensures that users who are not recruitment officers are not allowed to
        create a mail alias for the recruiting source while who are recruitment officers are
        """
        simple_user = new_test_user(self.env, 'smp',
            groups='base.group_user', name='Simple User', email='smp@example.com')
        interviewer_user = new_test_user(self.env, 'itw',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer', email='itw@example.com')
        recruitment_officer_user = new_test_user(self.env, 'rec_off',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_user',
            name='Recruitment Officer', email='rec_off@example.com')
        with self.assertRaises(AccessError):
            self.hr_recruitment_source.with_user(simple_user).create_alias()
        with self.assertRaises(AccessError):
            self.hr_recruitment_source.with_user(interviewer_user).create_alias()
        try:
            self.hr_recruitment_source.with_user(recruitment_officer_user).create_alias()
        except AccessError:
            self.fail("Recruitment Officer should be able to create mail alias for hr.recruitment.source.")
