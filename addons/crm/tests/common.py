# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.fields import Datetime
from odoo import tools

INCOMING_EMAIL = """Return-Path: {return_path}
X-Original-To: {to}
Delivered-To: {to}
Received: by mail.my.com (Postfix, from userid xxx)
    id 822ECBFB67; Mon, 24 Oct 2011 07:36:51 +0200 (CEST)
X-Spam-Checker-Version: SpamAssassin 3.3.1 (2010-03-16) on mail.my.com
X-Spam-Level: 
X-Spam-Status: No, score=-1.0 required=5.0 tests=ALL_TRUSTED autolearn=ham
    version=3.3.1
Received: from [192.168.1.146] 
    (Authenticated sender: {email_from})
    by mail.customer.com (Postfix) with ESMTPSA id 07A30BFAB4
    for <{to}>; Mon, 24 Oct 2011 07:36:50 +0200 (CEST)
Message-ID: {msg_id}
Date: Mon, 24 Oct 2011 11:06:29 +0530
From: {email_from}
User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.14) Gecko/20110223 Lightning/1.0b2 Thunderbird/3.1.8
MIME-Version: 1.0
To: {to}
Subject: {subject}
Content-Type: text/plain; charset=ISO-8859-1; format=flowed
Content-Transfer-Encoding: 8bit

This is an example email. All sensitive content has been stripped out.

ALL GLORY TO THE HYPNOTOAD !

Cheers,

Somebody."""


class TestCrmCommon(TestSalesCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super(TestCrmCommon, cls).setUpClass()
        cls._init_mail_gateway()

        cls.sales_team_1.write({
            'alias_name': 'sales.test',
            'use_leads': True,
            'use_opportunities': True,
        })

        (cls.user_sales_manager | cls.user_sales_leads | cls.user_sales_salesman).write({
            'groups_id': [(4, cls.env.ref('crm.group_use_lead').id)]
        })

        cls.env['crm.stage'].search([]).write({'sequence': 9999})  # ensure search will find test data first
        cls.stage_team1_1 = cls.env['crm.stage'].create({
            'name': 'New',
            'sequence': 1,
            'team_id': cls.sales_team_1.id,
        })
        cls.stage_team1_2 = cls.env['crm.stage'].create({
            'name': 'Proposition',
            'sequence': 5,
            'team_id': cls.sales_team_1.id,
        })
        cls.stage_team1_won = cls.env['crm.stage'].create({
            'name': 'Won',
            'sequence': 70,
            'team_id': cls.sales_team_1.id,
            'is_won': True,
        })
        cls.stage_gen_1 = cls.env['crm.stage'].create({
            'name': 'Generic stage',
            'sequence': 3,
            'team_id': False,
        })
        cls.stage_gen_won = cls.env['crm.stage'].create({
            'name': 'Generic Won',
            'sequence': 30,
            'team_id': False,
            'is_won': True,
        })

        # countries and langs
        cls.lang_en = cls.env['res.lang']._lang_get('en_US')

        # leads
        cls.lead_1 = cls.env['crm.lead'].create({
            'name': 'Nibbler Spacecraft Request',
            'type': 'lead',
            'user_id': cls.user_sales_leads.id,
            'team_id': cls.sales_team_1.id,
            'partner_id': False,
            'contact_name': 'Amy Wong',
            'email_from': 'amy.wong@test.example.com',
            'country_id': cls.env.ref('base.us').id,
        })
        # update lead_1: stage_id is not computed anymore by default for leads
        cls.lead_1.write({
            'stage_id': cls.stage_team1_1.id,
        })

        # create an history for new team
        cls.lead_team_1_won = cls.env['crm.lead'].create({
            'name': 'Already Won',
            'type': 'lead',
            'user_id': cls.user_sales_leads.id,
            'team_id': cls.sales_team_1.id,
        })
        cls.lead_team_1_won.action_set_won()
        cls.lead_team_1_lost = cls.env['crm.lead'].create({
            'name': 'Already Won',
            'type': 'lead',
            'user_id': cls.user_sales_leads.id,
            'team_id': cls.sales_team_1.id,
        })
        cls.lead_team_1_lost.action_set_lost()
        (cls.lead_team_1_won | cls.lead_team_1_lost).flush()

        # email / phone data
        cls.test_email_data = [
            '"Planet Express" <planet.express@test.example.com>',
            '"Philip, J. Fry" <philip.j.fry@test.example.com>',
            '"Turanga Leela" <turanga.leela@test.example.com>',
        ]
        cls.test_email_data_normalized = [
            'planet.express@test.example.com',
            'philip.j.fry@test.example.com',
            'turanga.leela@test.example.com',
        ]
        cls.test_phone_data = [
            '+1 202 555 0122',  # formatted US number
            '202 555 0999',  # local US number
            '202 555 0888',  # local US number
        ]
        cls.test_phone_data_sanitized = [
            '+12025550122',
            '+12025550999',
            '+12025550888',
        ]

        # create some test contact and companies
        cls.contact_company_1 = cls.env['res.partner'].create({
            'name': 'Planet Express',
            'email': cls.test_email_data[0],
            'is_company': True,
            'street': '57th Street',
            'city': 'New New York',
            'country_id': cls.env.ref('base.us').id,
            'zip': '12345',
        })
        cls.contact_1 = cls.env['res.partner'].create({
            'name': 'Philip J Fry',
            'email': cls.test_email_data[1],
            'mobile': cls.test_phone_data[0],
            'title': cls.env.ref('base.res_partner_title_mister').id,
            'function': 'Delivery Boy',
            'phone': False,
            'parent_id': cls.contact_company_1.id,
            'is_company': False,
            'street': 'Actually the sewers',
            'city': 'New York',
            'country_id': cls.env.ref('base.us').id,
            'zip': '54321',
        })
        cls.contact_2 = cls.env['res.partner'].create({
            'name': 'Turanga Leela',
            'email': cls.test_email_data[2],
            'mobile': cls.test_phone_data[1],
            'phone': cls.test_phone_data[2],
            'parent_id': False,
            'is_company': False,
            'street': 'Cookieville Minimum-Security Orphanarium',
            'city': 'New New York',
            'country_id': cls.env.ref('base.us').id,
            'zip': '97648',
        })

    def _create_leads_batch(self, lead_type='lead', count=10, partner_ids=None, user_ids=None):
        """ Helper tool method creating a batch of leads, useful when dealing
        with batch processes. Please update me.

        :param string type: 'lead', 'opportunity', 'mixed' (lead then opp),
          None (depends on configuration);
        """
        types = ['lead', 'opportunity']
        leads_data = [{
            'name': 'TestLead_%02d' % (x),
            'type': lead_type if lead_type else types[x % 2],
            'priority': '%s' % (x % 3),
        } for x in range(count)]

        # customer information
        if partner_ids:
            for idx, lead_data in enumerate(leads_data):
                lead_data['partner_id'] = partner_ids[idx % len(partner_ids)]
        else:
            for idx, lead_data in enumerate(leads_data):
                lead_data['email_from'] = tools.formataddr((
                    'TestCustomer_%02d' % (idx),
                    'customer_email_%02d@example.com' % (idx)
                ))

        # salesteam information
        if user_ids:
            for idx, lead_data in enumerate(leads_data):
                lead_data['user_id'] = user_ids[idx % len(user_ids)]

        return self.env['crm.lead'].create(leads_data)

    def _create_duplicates(self, lead, create_opp=True):
        """ Helper tool method creating, based on a given lead

          * a customer (res.partner) based on lead email (to test partner finding)
            -> FIXME: using same normalized email does not work currently, only exact email works
          * a lead with same email_from
          * a lead with same email_normalized (other email_from)
          * a lead with customer but another email
          * a lost opportunity with same email_from
        """
        self.customer = self.env['res.partner'].create({
            'name': 'Lead1 Email Customer',
            'email': lead.email_from,
        })
        self.lead_email_from = self.env['crm.lead'].create({
            'name': 'Duplicate: same email_from',
            'type': 'lead',
            'team_id': lead.team_id.id,
            'email_from': lead.email_from,
        })
        # self.lead_email_normalized = self.env['crm.lead'].create({
        #     'name': 'Duplicate: email_normalize comparison',
        #     'type': 'lead',
        #     'team_id': lead.team_id.id,
        #     'stage_id': lead.stage_id.id,
        #     'email_from': 'CUSTOMER WITH NAME <%s>' % lead.email_normalized.upper(),
        # })
        self.lead_partner = self.env['crm.lead'].create({
            'name': 'Duplicate: customer ID',
            'type': 'lead',
            'team_id': lead.team_id.id,
            'partner_id': self.customer.id,
        })
        if create_opp:
            self.opp_lost = self.env['crm.lead'].create({
                'name': 'Duplicate: lost opportunity',
                'type': 'opportunity',
                'team_id': lead.team_id.id,
                'stage_id': lead.stage_id.id,
                'email_from': lead.email_from,
            })
            self.opp_lost.action_set_lost()
        else:
            self.opp_lost = self.env['crm.lead']

        # self.assertEqual(self.lead_email_from.email_normalized, self.lead_email_normalized.email_normalized)
        # self.assertTrue(lead.email_from != self.lead_email_normalized.email_from)
        # self.assertFalse(self.opp_lost.active)

        # new_lead = self.lead_email_from | self.lead_email_normalized | self.lead_partner | self.opp_lost
        new_leads = self.lead_email_from | self.lead_partner | self.opp_lost
        new_leads.flush()  # compute notably probability
        return new_leads


class TestLeadConvertCommon(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertCommon, cls).setUpClass()
        # Sales Team organization
        # Role: M (team member) R (team manager)
        # SALESMAN---------------sales_team_1-----sales_team_convert
        # admin------------------M----------------/
        # user_sales_manager-----R----------------R
        # user_sales_leads-------M----------------/
        # user_sales_salesman----/----------------M

        # Stages Team organization
        # Name-------------------ST-------------------Sequ
        # stage_team1_1----------sales_team_1---------1
        # stage_team1_2----------sales_team_1---------5
        # stage_team1_won--------sales_team_1---------70
        # stage_gen_1------------/--------------------3
        # stage_gen_won----------/--------------------30
        # stage_team_convert_1---sales_team_convert---1

        cls.sales_team_convert = cls.env['crm.team'].create({
            'name': 'Convert Sales Team',
            'sequence': 10,
            'alias_name': False,
            'use_leads': True,
            'use_opportunities': True,
            'company_id': False,
            'user_id': cls.user_sales_manager.id,
            'member_ids': [(4, cls.user_sales_salesman.id)],
        })
        cls.stage_team_convert_1 = cls.env['crm.stage'].create({
            'name': 'New',
            'sequence': 1,
            'team_id': cls.sales_team_convert.id,
        })

        cls.lead_1.write({'date_open': Datetime.from_string('2020-01-15 11:30:00')})

        cls.crm_lead_dt_patcher = patch('odoo.addons.crm.models.crm_lead.fields.Datetime', wraps=Datetime)
        cls.crm_lead_dt_mock = cls.crm_lead_dt_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.crm_lead_dt_patcher.stop()
        super(TestLeadConvertCommon, cls).tearDownClass()


class TestLeadConvertMassCommon(TestLeadConvertCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertMassCommon, cls).setUpClass()
        # Sales Team organization
        # Role: M (team member) R (team manager)
        # SALESMAN-------------------sales_team_1-----sales_team_convert
        # admin----------------------M----------------/
        # user_sales_manager---------R----------------R
        # user_sales_leads-----------M----------------/
        # user_sales_leads_convert---/----------------M  <-- NEW
        # user_sales_salesman--------/----------------M

        cls.user_sales_leads_convert = mail_new_test_user(
            cls.env, login='user_sales_leads_convert',
            name='Lucien Sales Leads Convert', email='crm_leads_2@test.example.com',
            company_id=cls.env.ref("base.main_company").id,
            notification_type='inbox',
            groups='sales_team.group_sale_salesman_all_leads,base.group_partner_manager,crm.group_use_lead',
        )
        cls.sales_team_convert.write({
            'member_ids': [(4, cls.user_sales_leads_convert.id)]
        })

        cls.lead_w_partner = cls.env['crm.lead'].create({
            'name': 'New1',
            'type': 'lead',
            'probability': 10,
            'user_id': cls.user_sales_manager.id,
            'stage_id': False,
            'partner_id': cls.contact_1.id,
        })
        cls.lead_w_partner.write({'stage_id': False})
        cls.lead_w_partner_company = cls.env['crm.lead'].create({
            'name': 'New1',
            'type': 'lead',
            'probability': 15,
            'user_id': cls.user_sales_manager.id,
            'stage_id': cls.stage_team1_1.id,
            'partner_id': cls.contact_company_1.id,
            'contact_name': 'Hermes Conrad',
            'email_from': 'hermes.conrad@test.example.com',
        })
        cls.lead_w_contact = cls.env['crm.lead'].create({
            'name': 'LeadContact',
            'type': 'lead',
            'probability': 15,
            'contact_name': 'TestContact',
            'user_id': cls.user_sales_salesman.id,
            'stage_id': cls.stage_gen_1.id,
        })
        cls.lead_w_email = cls.env['crm.lead'].create({
            'name': 'LeadEmailAsContact',
            'type': 'lead',
            'probability': 15,
            'email_from': 'contact.email@test.example.com',
            'user_id': cls.user_sales_salesman.id,
            'stage_id': cls.stage_gen_1.id,
        })
        cls.lead_w_email_lost = cls.env['crm.lead'].create({
            'name': 'Lost',
            'type': 'lead',
            'probability': 15,
            'email_from': 'strange.from@test.example.com',
            'user_id': cls.user_sales_leads.id,
            'stage_id': cls.stage_team1_2.id,
            'active': False,
        })
        (cls.lead_w_partner | cls.lead_w_partner_company | cls.lead_w_contact | cls.lead_w_email | cls.lead_w_email_lost).flush()
