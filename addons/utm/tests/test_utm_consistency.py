# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.utm.models.utm_mixin import UtmMixin
from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install', 'utm', 'utm_consistency')
class TestUTMConsistency(TestUTMCommon):

    @users('user_employee_utm')
    def test_utm_consistency_utm_ref(self):
        """ The _utm_ref method was implemented defensively to increase robustness of important UTM
        data records. Make sure it behaves as expected:
        - Return None for references not inside the protected list
        - Return the existing data record if everything exists as expected
        - Create a new record and data record if inside the protected list and not found. """

        self.assertFalse(self.env['utm.mixin']._utm_ref('utm.fake_ref'))

        self.assertEqual(
            self.env['utm.mixin']._utm_ref('utm.utm_medium_email'),
            self.env.ref('utm.utm_medium_email'),
        )

        with patch.object(
            UtmMixin,
            'SELF_REQUIRED_UTM_REF',
            {'utm.new_ref': ('New UTM Source', 'utm.source')},
        ):
            self.assertFalse(self.env.ref('utm.new_ref', raise_if_not_found=False))
            new_utm = self.env['utm.mixin']._utm_ref('utm.new_ref')
            self.assertEqual(new_utm.name, 'New UTM Source')
            # make sure it also created a data record
            new_utm_from_ref = self.env.ref('utm.new_ref')
            self.assertEqual(new_utm_from_ref.name, 'New UTM Source')

    @users('__system__')
    def test_utm_consistency_unlink(self):
        """ You are not supposed to delete records from the 'utm_mixin.SELF_REQUIRED_UTM_REF' list.
        Indeed, those are essential to functional flows.
        e.g: The source 'Mass Mailing' and the medium 'Email' are used within Mass Mailing, HR, ...
        Deleting those records would prevent meaningful statistics and render UTM useless. """

        for xml_id in self.env['utm.mixin'].SELF_REQUIRED_UTM_REF:
            with self.assertRaises(UserError):
                self.env.ref(xml_id).unlink()
