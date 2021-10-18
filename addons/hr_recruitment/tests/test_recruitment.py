# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, TransactionCase

@tagged('recruitment')
class TestRecruitment(TransactionCase):

    def test_duplicate_email(self):
        # Tests that duplicate email match ignores case
        # And that no match is found when there is none
        dup1, dup2, no_dup = self.env['hr.applicant'].create([
            {
                'name': 'Application 1',
                'email_from': 'laurie.poiret@aol.ru',
            },
            {
                'name': 'Application 2',
                'email_from': 'laurie.POIRET@aol.ru',
            },
            {
                'name': 'Application 3',
                'email_from': 'laure.poiret@aol.ru',
            },
        ])
        self.assertEqual(dup1.application_count, 2)
        self.assertEqual(dup2.application_count, 2)
        self.assertEqual(no_dup.application_count, 1)
