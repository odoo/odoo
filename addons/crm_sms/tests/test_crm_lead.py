# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests.common import Form, users


class TestCRMLead(TestCrmCommon):

    @users('user_sales_manager')
    def test_phone_mobile_update(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'country_id': self.env.ref('base.us').id,
            'phone': self.test_phone_data[0],
        })
        self.assertEqual(lead.phone, self.test_phone_data[0])
        self.assertFalse(lead.mobile)
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[0])

        lead.write({'phone': False, 'mobile': self.test_phone_data[1]})
        self.assertFalse(lead.phone)
        self.assertEqual(lead.mobile, self.test_phone_data[1])
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[1])

        lead.write({'phone': self.test_phone_data[1], 'mobile': self.test_phone_data[2]})
        self.assertEqual(lead.phone, self.test_phone_data[1])
        self.assertEqual(lead.mobile, self.test_phone_data[2])
        self.assertEqual(lead.phone_sanitized, self.test_phone_data_sanitized[2])
