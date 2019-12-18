# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
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
            'team_id': cls.sales_team_1.id,
            'is_won': True,
            'sequence': 70,
        })
        cls.stage_gen_1 = cls.env['crm.stage'].create({
            'name': 'Generic stage',
            'sequence': 3,
            'team_id': False,
        })

        cls.lead_1 = cls.env['crm.lead'].create({
            'name': 'Club Office Furnitures',
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
