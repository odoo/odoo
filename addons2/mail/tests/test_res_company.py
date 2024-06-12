# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged, users


@tagged('res_company')
class TestCompany(MailCommon):

    @users('admin')
    def test_company_colors(self):
        """ Test primary and secondary color management, especially the choice
        between document colors and email-specific colors. When setting document
        layout colors, email colors are updated. When updating email colors
        layout is not updated, they are less important. """
        # propagate at create
        new_company = self.env['res.company'].create({
            'name': 'Test Colors',
            'primary_color': '#AAAAAA',
            'secondary_color': '#BBBBBB',
        })
        self.assertEqual(new_company.primary_color, '#AAAAAA')
        self.assertEqual(new_company.secondary_color, '#BBBBBB')
        self.assertEqual(new_company.email_primary_color, '#AAAAAA',
                         'Updating document colors changes email colors')
        self.assertEqual(new_company.email_secondary_color, '#BBBBBB',
                         'Updating document colors changes email colors')

        # email can be changed independently
        new_company.write({
            'email_primary_color': '#CCCCCC',
            'email_secondary_color': '#DDDDDD',
        })
        self.assertEqual(new_company.primary_color, '#AAAAAA',
                         'Updating email colors does not change global layout')
        self.assertEqual(new_company.secondary_color, '#BBBBBB',
                         'Updating email colors does not change global layout')
        self.assertEqual(new_company.email_primary_color, '#CCCCCC')
        self.assertEqual(new_company.email_secondary_color, '#DDDDDD')

        # reset document -> reset email
        new_company.write({
            'primary_color': '#EEEEEE',
            'secondary_color': '#FFFFFF',
        })
        self.assertEqual(new_company.primary_color, '#EEEEEE')
        self.assertEqual(new_company.secondary_color, '#FFFFFF')
        self.assertEqual(new_company.email_primary_color, '#EEEEEE',
                         'Updating document colors changes email colors')
        self.assertEqual(new_company.email_secondary_color, '#FFFFFF',
                         'Updating document colors changes email colors')
