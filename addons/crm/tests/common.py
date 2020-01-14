# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
from odoo.fields import Datetime
from odoo.tests.common import SavepointCase

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


class TestCrmCommon(MailCase, SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestCrmCommon, cls).setUpClass()
        cls._init_mail_gateway()

        cls.user_sales_manager = mail_new_test_user(
            cls.env, login='user_sales_manager',
            name='Martin Sales Manager', email='crm_manager@test.example.com',
            company_id=cls.env.ref("base.main_company").id,
            notification_type='inbox',
            groups='sales_team.group_sale_manager,base.group_partner_manager,crm.group_use_lead',
        )
        cls.user_sales_leads = mail_new_test_user(
            cls.env, login='user_sales_leads',
            name='Laetitia Sales Leads', email='crm_leads@test.example.com',
            company_id=cls.env.ref("base.main_company").id,
            notification_type='inbox',
            groups='sales_team.group_sale_salesman_all_leads,base.group_partner_manager,crm.group_use_lead',
        )
        cls.user_sales_salesman = mail_new_test_user(
            cls.env, login='user_sales_salesman',
            name='Orteil Sales Own', email='crm_salesman@test.example.com',
            company_id=cls.env.ref("base.main_company").id,
            notification_type='inbox',
            groups='sales_team.group_sale_salesman,crm.group_use_lead',
        )

        cls.sales_team_1 = cls.env['crm.team'].create({
            'name': 'Test Sales Team',
            'alias_name': 'sales.test',
            'use_leads': True,
            'use_opportunities': True,
            'company_id': False,
            'user_id': cls.user_sales_manager.id,
            'member_ids': [(4, cls.user_sales_leads.id), (4, cls.env.ref('base.user_admin').id)],
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

        cls.lead_1 = cls.env['crm.lead'].create({
            'name': 'Nibbler Spacecraft Request',
            'type': 'lead',
            'user_id': cls.user_sales_leads.id,
            'team_id': cls.sales_team_1.id,
            'contact_name': 'Amy Wong',
            'email_from': 'amy.wong@test.example.com',
        })

        cls.contact_company_1 = cls.env['res.partner'].create({
            'name': 'Planet Express',
            'email': 'planet.express@test.example.com',
            'is_company': True,
            'street': '57th Street',
            'city': 'New New York',
            'country_id': cls.env.ref('base.us').id,
            'zip': '12345',
        })
        cls.contact_1 = cls.env['res.partner'].create({
            'name': 'Philip J Fry',
            'email': 'philip.j.fry@test.example.com',
            'mobile': '+1 202 555 0122',
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
            'email': 'turanga.leela@test.example.com',
            'parent_id': False,
            'is_company': False,
            'street': 'Cookieville Minimum-Security Orphanarium',
            'city': 'New New York',
            'country_id': cls.env.ref('base.us').id,
            'zip': '97648',
        })

    def _create_duplicates(self, lead, count=2):
        leads = self.env['crm.lead']
        for x in range(count):
            leads |= self.env['crm.lead'].create({
                'name': 'Dup-%02d-%s' % (x+1, lead.name),
                'type': 'lead',
                'user_id': False,
                'team_id': lead.team_id.id,
                'contact_name': 'Duplicate %02d of %s' % (x+1, lead.contact_name),
                'email_from': lead.email_from,
            })
        return leads


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
        for l in (cls.lead_w_partner | cls.lead_w_partner_company | cls.lead_w_contact | cls.lead_w_email | cls.lead_w_email_lost):
            l._onchange_user_id()
            l.flush()
