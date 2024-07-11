# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.iap.tools import iap_tools
from odoo.tests.common import tagged, users


@tagged('lead_internals')
class TestCRMLead(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # To avoid magic phone sanitization
        cls.env.company.country_id = cls.env.ref('base.us')

        cls.emails_provider_generic = {
            ('robert.poilvert@gmail.com', 'robert.poilvert@gmail.com'),
            ('fp@odoo.com', 'fp@odoo.com'),
            ('fp.alias@mail.odoo.com', 'fp.alias@mail.odoo.com'),
        }
        cls.emails_provider_company = {
            ('robert.poilvert@mycompany.com', 'mycompany.com'),
            ('fp@subdomain.odoo.com', 'subdomain.odoo.com'),
        }

        # customer data
        country_us_id = cls.env.ref('base.us').id
        cls.test_company = cls.env['res.partner'].create({
            'city': 'New New York',
            'country_id': country_us_id,
            'email': 'test.company@another.email.company.com',
            'is_company': True,
            'name': 'My company',
            'street': '57th Street',
            'zip': '12345',
        })
        cls.test_partners = cls.env['res.partner'].create([
            {
                'city': 'New York',
                'country_id': country_us_id,
                'email': 'dave@another.email.company.com',
                'is_company': False,
                'mobile': '+1 202 000 0123',
                'name': 'Dave',
                'phone': False,
                'parent_id': cls.test_company.id,
                'street': 'Pearl street',
                'zip': '12345',
            },
            {
                'city': 'New York',
                'country_id': country_us_id,
                'email': 'eve@another.email.company.com',
                'is_company': False,
                'mobile': '+1 202 000 3210',
                'name': 'Eve',
                'parent_id': cls.test_company.id,
                'phone': False,
                'street': 'Wall street',
                'zip': '12345',
            }
        ])

        # base leads on which duplicate detection is performed
        cls.lead_generic = cls.env['crm.lead'].create({
            'country_id': country_us_id,
            'email_from': 'FP@odoo.com',
            'name': 'Generic 1',
            'mobile': False,
            'partner_id': cls.test_partners[0].id,
            'phone': '+1 202 555 0123',
            'type': 'lead',
        })
        cls.lead_company = cls.env['crm.lead'].create({
            'country_id': country_us_id,
            'email_from': 'floppy@MYCOMPANY.com',
            'mobile': '+1 202 666 4567',
            'partner_id': False,
            'name': 'CompanyMail 1',
            'phone': False,
            'type': 'lead',
        })

        # duplicates
        cls.lead_generic_email_dupes = cls.env['crm.lead'].create([
            # email based: normalized version used for email domain criterion
            {
                'email_from': '"Fabulous Fab" <fp@ODOO.COM>',
                'name': 'Dupe1 of fp@odoo.com (same email)',
                'type': 'lead',
            },
            {
                'email_from': 'FP@odoo.com',
                'name': 'Dupe2 of fp@odoo.com (same email)',
                'type': 'lead',
            },
            # phone_sanitized based
            {
                'email_from': 'not.fp@not.odoo.com',
                'name': 'Dupe3 of fp@odoo.com (same phone sanitized)',
                'phone': '+1 202 555 0123',
                'type': 'lead',
            },
            {
                'email_from': 'not.fp@not.odoo.com',
                'mobile': '+1 202 555 0123',
                'name': 'Dupe4 of fp@odoo.com (same phone sanitized)',
                'type': 'lead',
            },
            # same commercial entity
            {
                'name': 'Dupe5 of fp@odoo.com (same commercial entity)',
                'partner_id': cls.test_partners[1].id,
            },
            {
                'name': 'Dupe6 of fp@odoo.com (same commercial entity)',
                'partner_id': cls.test_company.id,
            }
        ])
        cls.lead_generic_email_notdupes = cls.env['crm.lead'].create([
            # email: check for exact match
            {
                'email_from': 'not.fp@odoo.com',
                'name': 'NotADupe1',
                'type': 'lead',
            },
        ])
        cls.lead_company_email_dupes = cls.env['crm.lead'].create([
            # email based: normalized version used for email domain criterion
            {
                'email_from': '"The Other Fabulous Fab" <fp@mycompany.COM>',
                'name': 'Dupe1 of mycompany@mycompany.com (same company)',
                'type': 'lead',
            },
            {
                'email_from': '"Same Email" <floppy@mycompany.com>',
                'name': 'Dupe2 of mycompany@mycompany.com (same company)',
                'type': 'lead',
            },
            # phone_sanitized based
            {
                'email_from': 'not.floppy@not.mycompany.com',
                'name': 'Dupe3 of fp@odoo.com (same phone sanitized)',
                'phone': '+1 202 666 4567',
                'type': 'lead',
            },
            {
                'email_from': 'not.floppy@not.mycompany.com',
                'mobile': '+1 202 666 4567',
                'name': 'Dupe4 of fp@odoo.com (same phone sanitized)',
                'type': 'lead',
            },
        ])
        cls.lead_company_email_notdupes = cls.env['crm.lead'].create([
            # email: check same company
            {
                'email_from': 'floppy@zboing.MYCOMPANY.com',
                'name': 'NotADupe2',
                'type': 'lead',
            },
        ])

    def test_assert_initial_values(self):
        """ Just be sure of initial value for those tests """
        lead_generic = self.lead_generic.with_env(self.env)
        self.assertEqual(lead_generic.phone_sanitized, '+12025550123')
        self.assertEqual(lead_generic.email_domain_criterion, 'fp@odoo.com')
        self.assertEqual(lead_generic.email_normalized, 'fp@odoo.com')

        lead_company = self.lead_company.with_env(self.env)
        self.assertEqual(lead_company.phone_sanitized, '+12026664567')
        self.assertEqual(lead_company.email_domain_criterion, '@mycompany.com')
        self.assertEqual(lead_company.email_normalized, 'floppy@mycompany.com')

    @users('user_sales_leads')
    def test_crm_lead_duplicates_fetch(self):
        """ Test heuristic to find duplicates of a given lead. """
        # generic provider-based email
        lead_generic = self.lead_generic.with_env(self.env)

        self.assertEqual(lead_generic.duplicate_lead_ids,
                         lead_generic + self.lead_generic_email_dupes,
                         'Duplicates: exact email matching (+ self)')

        # company-based email
        lead_company = self.lead_company.with_env(self.env)
        self.assertEqual(lead_company.duplicate_lead_ids,
                         lead_company + self.lead_company_email_dupes,
                         'Duplicates: exact email matching (+ self)')

    @users('user_sales_leads')
    def test_crm_lead_email_domain_criterion(self):
        """ Test computed field 'email_domain_criterion' used notably to fetch
        duplicates. """
        for test_email, provider in self.emails_provider_generic:
            with self.subTest(test_email=test_email, provider=provider):
                lead = self.env['crm.lead'].create({
                    'email_from': test_email,
                    'name': test_email,
                })
                self.assertEqual(lead.email_domain_criterion, provider)

        for test_email, provider in self.emails_provider_company:
            with self.subTest(test_email=test_email, provider=provider):
                lead = self.env['crm.lead'].create({
                    'email_from': test_email,
                    'name': test_email,
                })
                self.assertEqual(lead.email_domain_criterion, f'@{provider}',)

    @users('user_sales_leads')
    def test_iap_tools(self):
        """ Test iap tools specifically """
        for test_email, provider in self.emails_provider_generic:
            with self.subTest(test_email=test_email, provider=provider):
                self.assertEqual(
                    iap_tools.mail_prepare_for_domain_search(test_email),
                    test_email,
                    'As provider is a generic one, complete email should be returned for a company-based mail search'
                )

        for test_email, provider in self.emails_provider_company:
            with self.subTest(test_email=test_email, provider=provider):
                self.assertEqual(
                    iap_tools.mail_prepare_for_domain_search(test_email),
                    f'@{provider}',
                    'As provider is a company one, only the domain part should be returned for a company-based mail search'
                )
