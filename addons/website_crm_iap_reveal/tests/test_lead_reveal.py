# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.website_crm_iap_reveal.tests.common import MockIAPReveal
from odoo.tests.common import users


class TestLeadMine(TestCrmCommon, MockIAPReveal):

    @classmethod
    def setUpClass(cls):
        super(TestLeadMine, cls).setUpClass()
        cls.registry.enter_test_mode(cls.cr)

        cls.test_industry_tags = cls.env.ref('crm_iap_mine.crm_iap_mine_industry_33') + cls.env.ref('crm_iap_mine.crm_iap_mine_industry_148')
        cls.test_roles = cls.env.ref('crm_iap_mine.crm_iap_mine_role_11') + cls.env.ref('crm_iap_mine.crm_iap_mine_role_19')
        cls.test_seniority = cls.env.ref('crm_iap_mine.crm_iap_mine_seniority_2')

        cls.test_crm_tags = cls.env['crm.tag'].create([
            {'name': 'TestTag1'},
            {'name': 'TestTag2'}
        ])
        cls.test_request_1 = cls.env['crm.reveal.rule'].create({
            'contact_filter_type': 'role',
            'extra_contacts': 3,
            'industry_tag_ids': cls.test_industry_tags.ids,
            'lead_for': 'people',
            'lead_type': 'lead',
            'name': 'Test Reveal People',
            'other_role_ids': cls.test_roles.ids,
            'preferred_role_id': cls.test_roles[0].id,
            'priority': '2',
            'seniority_id': cls.test_seniority.id,
            'suffix': '-ts1',
            'tag_ids': [(6, 0, cls.test_crm_tags.ids)],
            'team_id':  cls.sales_team_1.id,
            'user_id': cls.user_sales_leads.id,
        })
        cls.test_request_2 = cls.env['crm.reveal.rule'].create({
            'contact_filter_type': 'role',
            'industry_tag_ids': cls.test_industry_tags.ids,
            'lead_for': 'companies',
            'lead_type': 'opportunity',
            'name': 'Test Reveal Companies',
            'priority': '2',
            'suffix': '-ts2',
            'tag_ids': [(6, 0, cls.test_crm_tags.ids)],
            'team_id':  cls.sales_team_1.id,
            'user_id': cls.user_admin.id,
        })
        cls.env['crm.reveal.view'].search([]).unlink()
        cls.test_views = cls.env['crm.reveal.view'].create([
            {'reveal_ip': '90.80.70.60',
             'reveal_rule_id': cls.test_request_1.id,
             'reveal_state': 'to_process',
            },
            {'reveal_ip': '90.80.70.61',
             'reveal_rule_id': cls.test_request_1.id,
             'reveal_state': 'to_process',
            },
            {'reveal_ip': '90.80.70.70',
             'reveal_rule_id': cls.test_request_2.id,
             'reveal_state': 'to_process',
            }
        ])

        cls.ip_to_rules = [
            {'ip': '90.80.70.60', 'rules': cls.test_request_1},
            {'ip': '90.80.70.61', 'rules': cls.test_request_1},
            {'ip': '90.80.70.70', 'rules': cls.test_request_2},
        ]

    @classmethod
    def tearDownClass(cls):
        cls.registry.leave_test_mode()
        super().tearDownClass()

    @users('user_sales_manager')
    def test_reveal_error_credit(self):
        # check initial state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.test_views
        )

        with self.mock_IAP_reveal(self.ip_to_rules, sim_error='credit'):
            self.env['crm.reveal.rule']._process_lead_generation(autocommit=False)

        # check initial state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.test_views
        )
        self.assertEqual(set(self.test_views.mapped('reveal_state')), set(['to_process']))

    @users('user_sales_manager')
    def test_reveal_error_jsonrpc_exception(self):
        # check initial state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.test_views
        )

        with self.assertRaises(exceptions.UserError):
            with self.mock_IAP_reveal(self.ip_to_rules, sim_error='jsonrpc_exception'):
                self.env['crm.reveal.rule']._process_lead_generation(autocommit=False)

        # check initial state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.test_views
        )
        self.assertEqual(set(self.test_views.mapped('reveal_state')), set(['to_process']))

    @users('user_sales_manager')
    def test_reveal_error_no_result(self):
        # check initial state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.test_views
        )

        with self.mock_IAP_reveal(self.ip_to_rules, sim_error='no_result'):
            self.env['crm.reveal.rule']._process_lead_generation(autocommit=False)

        # check initial state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.test_views
        )
        self.assertEqual(set(self.test_views.mapped('reveal_state')), set(['not_found']))

    @users('user_sales_manager')
    def test_reveal(self):
        country_de = self.base_de
        state_de = self.de_state_st

        # check initial state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.test_views
        )

        with self.mock_IAP_reveal(self.ip_to_rules, name_list=['Heinrich', 'Rivil', 'LidGen']):
            self.env['crm.reveal.rule']._process_lead_generation(autocommit=False)

        # check post state of views
        self.assertEqual(
            self.env['crm.reveal.view'].search([('reveal_ip', 'in', ['90.80.70.60', '90.80.70.61', '90.80.70.70'])]),
            self.env['crm.reveal.view'], 'Views should have been unlinked after completion'
        )

        self.assertEqual(len(self._new_leads), 3, 'Number of leads should match IPs addresses')
        for counter, base_name in enumerate(['Heinrich', 'Rivil', 'LidGen']):
            if counter == 2:
                rule = self.test_request_2
            else:
                rule = self.test_request_1

            lead = self._new_leads.filtered(lambda lead: lead.name == '%s GmbH - %s' % (base_name, rule.suffix))
            self.assertTrue(bool(lead))

            # mine information
            self.assertEqual(lead.type, 'lead' if rule == self.test_request_1 else 'opportunity')
            self.assertEqual(lead.tag_ids, self.test_crm_tags)
            self.assertEqual(lead.team_id, self.sales_team_1)
            self.assertEqual(lead.user_id, self.user_sales_leads if rule == self.test_request_1 else self.user_admin)
            # iap
            self.assertEqual(lead.reveal_id, '123_ClearbitID_%s' % base_name, 'Ensure reveal_id is set to clearbit ID')
            # clearbit information
            if rule == self.test_request_1:  # people-based
                self.assertEqual(lead.contact_name, 'Contact %s 0' % base_name)
            else:
                self.assertFalse(lead.contact_name)
            self.assertEqual(lead.city, 'Mönchengladbach')
            self.assertEqual(lead.country_id, country_de)
            if rule == self.test_request_1:  # people-based
                self.assertEqual(lead.email_from, 'test.contact.0@%s.example.com' % base_name,
                                 'Lead email should be the one from first contact if search_type people is given')
            else:
                self.assertEqual(lead.email_from, 'info@%s.example.com' % base_name,
                                 'Lead email should be the one from company data as there is no contact')
            if rule == self.test_request_1:  # people-based
                self.assertEqual(lead.function, 'Doing stuff')
            else:
                self.assertFalse(lead.function)
            self.assertFalse(lead.partner_id)
            self.assertEqual(lead.partner_name, '%s GmbH legal_name' % base_name)
            self.assertEqual(lead.phone, '+4930499193937')
            self.assertEqual(lead.state_id, state_de)
            self.assertEqual(lead.street, 'Mennrather Str. 123456')
            self.assertEqual(lead.website, 'https://www.%s.de' % base_name)
            self.assertEqual(lead.zip, '41179')
