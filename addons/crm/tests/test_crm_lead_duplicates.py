# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadConvert(TestCrmCommon):

    @users('user_sales_manager')
    def test_potential_duplicates(self):
        company = self.env['res.partner'].create({
            'name': 'My company',
            'email': 'mycompany@company.com',
            'is_company': True,
            'street': '57th Street',
            'city': 'New New York',
            'country_id': self.env.ref('base.us').id,
            'zip': '12345',
        })

        partner_1 = self.env['res.partner'].create({
            'name': 'Dave',
            'email': 'dave@odoo.com',
            'mobile': '+1 202 555 0123',
            'phone': False,
            'parent_id': company.id,
            'is_company': False,
            'street': 'Pearl street',
            'city': 'California',
            'country_id': self.env.ref('base.us').id,
            'zip': '95826',
        })
        partner_2 = self.env['res.partner'].create({
            'name': 'Eve',
            'email': 'eve@odoo.com',
            'mobile': '+1 202 555 3210',
            'phone': False,
            'parent_id': company.id,
            'is_company': False,
            'street': 'Wall street',
            'city': 'New York',
            'country_id': self.env.ref('base.us').id,
            'zip': '54321',
        })

        lead_1 = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'type': 'lead',
            'partner_name': 'Alice',
            'email_from': 'alice@odoo.com',
        })
        lead_2 = self.env['crm.lead'].create({
            'name': 'Opportunity 1',
            'type': 'opportunity',
            'email_from': 'alice@odoo.com',
        })
        lead_3 = self.env['crm.lead'].create({
            'name': 'Opportunity 2',
            'type': 'opportunity',
            'email_from': 'alice@odoo.com',
        })
        lead_4 = self.env['crm.lead'].create({
            'name': 'Lead 2',
            'type': 'lead',
            'partner_name': 'Alice Doe'
        })
        lead_5 = self.env['crm.lead'].create({
            'name': 'Opportunity 3',
            'type': 'opportunity',
            'partner_name': 'Alice Doe'
        })
        lead_6 = self.env['crm.lead'].create({
            'name': 'Opportunity 4',
            'type': 'opportunity',
            'partner_name': 'Bob Doe'
        })
        lead_7 = self.env['crm.lead'].create({
            'name': 'Opportunity 5',
            'type': 'opportunity',
            'partner_name': 'Bob Doe',
            'email_from': 'bob@odoo.com',
        })
        lead_8 = self.env['crm.lead'].create({
            'name': 'Opportunity 6',
            'type': 'opportunity',
            'email_from': 'bob@mymail.com',
        })
        lead_9 = self.env['crm.lead'].create({
            'name': 'Opportunity 7',
            'type': 'opportunity',
            'email_from': 'alice@mymail.com',
        })
        lead_10 = self.env['crm.lead'].create({
            'name': 'Opportunity 8',
            'type': 'opportunity',
            'probability': 0,
            'active': False,
            'email_from': 'alice@mymail.com',
        })
        lead_11 = self.env['crm.lead'].create({
            'name': 'Opportunity 9',
            'type': 'opportunity',
            'contact_name': 'charlie'
        })
        lead_12 = self.env['crm.lead'].create({
            'name': 'Opportunity 10',
            'type': 'opportunity',
            'contact_name': 'Charlie Chapelin',
        })
        lead_13 = self.env['crm.lead'].create({
            'name': 'Opportunity 8',
            'type': 'opportunity',
            'partner_id': partner_1.id
        })
        lead_14 = self.env['crm.lead'].create({
            'name': 'Lead 3',
            'type': 'lead',
            'partner_id': partner_2.id
        })

        self.assertEqual(lead_1 + lead_2 + lead_3, lead_1.duplicate_lead_ids)
        self.assertEqual(lead_1 + lead_2 + lead_3, lead_2.duplicate_lead_ids)
        self.assertEqual(lead_1 + lead_2 + lead_3, lead_3.duplicate_lead_ids)
        self.assertEqual(lead_4 + lead_5, lead_4.duplicate_lead_ids)
        self.assertEqual(lead_4 + lead_5, lead_5.duplicate_lead_ids)
        self.assertEqual(lead_6 + lead_7, lead_6.duplicate_lead_ids)
        self.assertEqual(lead_6 + lead_7, lead_7.duplicate_lead_ids)
        self.assertEqual(lead_8 + lead_9 + lead_10, lead_8.duplicate_lead_ids)
        self.assertEqual(lead_8 + lead_9 + lead_10, lead_9.duplicate_lead_ids)
        self.assertEqual(lead_8 + lead_9 + lead_10, lead_10.duplicate_lead_ids)
        self.assertEqual(lead_11 + lead_12, lead_11.duplicate_lead_ids)
        self.assertEqual(lead_12, lead_12.duplicate_lead_ids)
        self.assertEqual(lead_13 + lead_14, lead_13.duplicate_lead_ids)
        self.assertEqual(lead_13 + lead_14, lead_14.duplicate_lead_ids)

    @users('user_sales_manager')
    def test_potential_duplicates_with_phone(self):
        customer = self.env['res.partner'].create({
            'email': 'customer1@duplicate.example.com',
            'mobile': '+32485001122',
            'name': 'Customer1',
            'phone': '(803)-456-6126',
        })
        base_lead = self.env['crm.lead'].create({
            'name': 'Base Lead',
            'partner_id': customer.id,
            'type': 'lead',
        })

        self.assertEqual(base_lead.contact_name, customer.name)
        self.assertEqual(base_lead.mobile, customer.mobile)
        self.assertFalse(base_lead.partner_name)
        self.assertEqual(base_lead.phone, customer.phone)

        dup1_1 = self.env['crm.lead'].create({
            'name': 'Base Lead Dup1',
            'type': 'lead',
            'phone': '456-6126',  # shorter version of base_lead
            'mobile': '             ', # empty string shouldn't crash Odoo
            'partner_name': 'Partner Name 1',
        })
        dup1_2 = self.env['crm.lead'].create({
            'name': 'Base Lead Dup2',
            'mobile': '8034566126',
            'partner_name': 'Partner Name 2',
            'type': 'lead',
        })
        dup1_3 = self.env['crm.lead'].create({
            'name': 'Base Lead Dup3',
            'partner_name': 'Partner Name 3',
            'phone': '(803)-456-6126',
            'type': 'lead',
        })
        dup1_4 = self.env['crm.lead'].create({
            'mobile': '0032485001122',
            # 'mobile': '0485001122',  # note: does not work
            'name': 'Base Lead Dup4',
            'partner_name': 'Partner Name 4',
            'phone': False,
            'type': 'lead',
        })

        expected = base_lead + dup1_2 + dup1_3 + dup1_4  # dup1_1 is shorter than lead -> not a dupe
        self.assertEqual(
            base_lead.duplicate_lead_ids, expected,
            'CRM: missing %s, extra %s' % ((expected - base_lead.duplicate_lead_ids).mapped('name'), (base_lead.duplicate_lead_ids - expected).mapped('name'))
        )
        expected = base_lead + dup1_1 + dup1_2 + dup1_3  # dup1_4 has mobile of customer, but no link with dup1_1
        self.assertEqual(
            dup1_1.duplicate_lead_ids, expected,
            'CRM: missing %s, extra %s' % ((expected - dup1_1.duplicate_lead_ids).mapped('name'), (dup1_1.duplicate_lead_ids - expected).mapped('name'))
        )

    @users('user_sales_manager')
    def test_potential_duplicates_with_invalid_email(self):
        lead_1 = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'type': 'lead',
            'email_from': 'mail"1@mymail.com'
        })
        lead_2 = self.env['crm.lead'].create({
            'name': 'Opportunity 1',
            'type': 'opportunity',
            'email_from': 'mail2@mymail.com'
        })
        lead_3 = self.env['crm.lead'].create({
            'name': 'Opportunity 2',
            'type': 'lead',
            'email_from': 'odoo.com'
        })
        lead_4 = self.env['crm.lead'].create({
            'name': 'Opportunity 3',
            'type': 'opportunity',
            'email_from': 'odoo.com'
        })
        lead_5 = self.env['crm.lead'].create({
            'name': 'Opportunity 3',
            'type': 'opportunity',
            'email_from': 'myodoo.com'
        })

        self.assertEqual(lead_1 + lead_2, lead_1.duplicate_lead_ids)
        self.assertEqual(lead_1 + lead_2, lead_2.duplicate_lead_ids)
        self.assertEqual(lead_3 + lead_4 + lead_5, lead_3.duplicate_lead_ids)
        self.assertEqual(lead_3 + lead_4 + lead_5, lead_4.duplicate_lead_ids)
        self.assertEqual(lead_5, lead_5.duplicate_lead_ids)
