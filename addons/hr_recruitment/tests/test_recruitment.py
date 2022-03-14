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
        self.assertEqual(dup1.application_count, 1)
        self.assertEqual(dup2.application_count, 1)
        self.assertEqual(no_dup.application_count, 0)

    def test_application_count(self):
        """ Test that we find same applicants based on simmilar mail,
            phone or mobile phone.
        """
        A, B, C, D, E, F = self.env['hr.applicant'].create([
            {
                'name': 'Application A',
                'email_from': 'abc@odoo.com',
                'partner_phone': '123',
                'partner_mobile': '14-15-16',
            },
            {
                'name': 'Application B',
                'partner_phone': '456',
                'partner_mobile': '11-12-13',
            },
            {
                'name': 'Application C',
                'email_from': 'def@odoo.com',
                'partner_phone': '123',
                'partner_mobile': '14-15-16',
            },
            {
                'name': 'Application D',
                'email_from': 'def@odoo.com',
                'partner_phone': '456',
                'partner_mobile': '14-15-16',
            },
            {
                'name': 'Application E',
            },
            {
                'name': 'Application F',
                'partner_phone': '11-12-13', # In case phone is configured in a wrong field
            }
        ])
        self.assertEqual(A.application_count, 2) # C, D
        self.assertEqual(B.application_count, 2) # D, F
        self.assertEqual(C.application_count, 2) # A, D
        self.assertEqual(D.application_count, 3) # A, B, C
        self.assertEqual(E.application_count, 0)
        self.assertEqual(F.application_count, 1) # B
