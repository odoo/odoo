# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo.addons.crm.models.crm_lead import PARTNER_ADDRESS_FIELDS_TO_SYNC
from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.fields import Datetime
from odoo import models, tools

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

ALL GLORY TO THE HYPNOTOAD!

Cheers,

Somebody."""


class TestCrmCommon(TestSalesCommon, MailCase):

    FIELDS_FIRST_SET = [
        'name', 'partner_id', 'campaign_id', 'company_id', 'country_id',
        'team_id', 'state_id', 'stage_id', 'medium_id', 'source_id', 'user_id',
        'title', 'city', 'contact_name', 'mobile', 'partner_name',
        'phone', 'probability', 'expected_revenue', 'street', 'street2', 'zip',
        'create_date', 'date_automation_last', 'email_from', 'email_cc', 'website'
    ]
    merge_fields = ['description', 'type', 'priority']

    @classmethod
    def setUpClass(cls):
        super(TestCrmCommon, cls).setUpClass()
        cls._init_mail_gateway()

        # Salesmen organization
        # ------------------------------------------------------------
        # Role: M (team member) R (team manager)
        # SALESMAN---------------sales_team_1
        # admin------------------M-----------
        # user_sales_manager-----R-----------
        # user_sales_leads-------M-----------
        # user_sales_salesman----/-----------

        # Sales teams organization
        # ------------------------------------------------------------
        # SALESTEAM-----------SEQU-----COMPANY
        # sales_team_1--------5--------False
        # data----------------9999-----??

        cls.sales_team_1.write({
            'alias_name': 'sales.test',
            'use_leads': True,
            'use_opportunities': True,
            'assignment_domain': False,
        })
        cls.sales_team_1_m1.write({
            'assignment_max': 45,
            'assignment_domain': False,
        })
        cls.sales_team_1_m2.write({
            'assignment_max': 15,
            'assignment_domain': False,
        })

        (cls.user_sales_manager + cls.user_sales_leads + cls.user_sales_salesman).write({
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
        base_us = cls.env.ref('base.us')
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.env['res.lang']._activate_lang('en_US')
        cls.lang_en = cls.env['res.lang']._lang_get('en_US')
        cls.lang_fr = cls.env['res.lang']._lang_get('fr_FR')

        # leads
        cls.lead_1 = cls.env['crm.lead'].create({
            'name': 'Nibbler Spacecraft Request',
            'type': 'lead',
            'user_id': cls.user_sales_leads.id,
            'team_id': cls.sales_team_1.id,
            'partner_id': False,
            'contact_name': 'Amy Wong',
            'email_from': 'amy.wong@test.example.com',
            'lang_id': cls.lang_fr.id,
            'phone': '+1 202 555 9999',
            'country_id': cls.env.ref('base.us').id,
            'probability': 20,
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
        (cls.lead_team_1_won + cls.lead_team_1_lost).flush_recordset()

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
            'lang': cls.lang_en.code,
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
            'lang': cls.lang_en.code,
            'mobile': cls.test_phone_data[1],
            'phone': cls.test_phone_data[2],
            'parent_id': False,
            'is_company': False,
            'street': 'Cookieville Minimum-Security Orphanarium',
            'city': 'New New York',
            'country_id': cls.env.ref('base.us').id,
            'zip': '97648',
        })
        cls.contact_company = cls.env['res.partner'].create({
            'name': 'Mom',
            'company_name': 'MomCorp',
            'is_company': True,
            'street': 'Mom Friendly Robot Street',
            'city': 'New new York',
            'country_id': base_us.id,
            'lang': cls.lang_en.code,
            'mobile': '+1 202 555 0888',
            'zip': '87654',
        })

        # test activities
        cls.activity_type_1 = cls.env['mail.activity.type'].create({
            'name': 'Lead Test Activity 1',
            'summary': 'ACT 1 : Presentation, barbecue, ... ',
            'res_model': 'crm.lead',
            'category': 'meeting',
            'delay_count': 5,
        })
        cls.env['ir.model.data'].create({
            'name': cls.activity_type_1.name.lower().replace(' ', '_'),
            'module': 'crm',
            'model': cls.activity_type_1._name,
            'res_id': cls.activity_type_1.id,
        })

    @classmethod
    def _activate_multi_company(cls):
        cls.company_2 = cls.env['res.company'].create({
            'country_id': cls.env.ref('base.au').id,
            'currency_id': cls.env.ref('base.AUD').id,
            'email': 'company.2@test.example.com',
            'name': 'New Test Company',
        })
        cls.alias_bounce_c2 = 'bounce.c2'
        cls.alias_catchall_c2 = 'catchall.c2'
        cls.alias_default_from_c2 = 'notifications.c2'
        cls.alias_domain_c2_name = 'test.mycompany2.com'
        cls.mail_alias_domain_c2 = cls.env['mail.alias.domain'].create({
            'bounce_alias': cls.alias_bounce_c2,
            'catchall_alias': cls.alias_catchall_c2,
            'company_ids': [(4, cls.company_2.id)],
            'default_from': cls.alias_default_from_c2,
            'name': cls.alias_domain_c2_name,
            'sequence': 2,
        })

        cls.user_sales_manager_mc = mail_new_test_user(
            cls.env,
            company_id=cls.company_2.id,
            company_ids=[(4, cls.company_main.id), (4, cls.company_2.id)],
            email='user.sales.manager.mc@test.example.com',
            login='user_sales_manager_mc',
            groups='sales_team.group_sale_manager,base.group_partner_manager',
            name='Myrddin Sales Manager',
            notification_type='inbox',
        )
        cls.team_company2 = cls.env['crm.team'].create({
            'company_id': cls.company_2.id,
            'name': 'C2 Team',
            'sequence': 10,
            'user_id': False,
        })
        cls.team_company2_m1 = cls.env['crm.team.member'].create({
            'crm_team_id': cls.team_company2.id,
            'user_id': cls.user_sales_manager_mc.id,
            'assignment_max': 30,
            'assignment_domain': False,
        })

        cls.team_company1 = cls.env['crm.team'].create({
            'company_id': cls.company_main.id,
            'name': 'MainCompany Team',
            'sequence': 50,
            'user_id': cls.user_sales_manager.id,
        })

        cls.partner_c2 = cls.env['res.partner'].create({
            'company_id': cls.company_2.id,
            'email': '"Partner C2" <partner_c2@multicompany.example.com>',
            'name': 'Customer for C2',
            'phone': '+32455001122',
        })

    def _create_leads_batch(self, lead_type='lead', count=10, email_dup_count=0,
                            partner_count=0, partner_ids=None, user_ids=None,
                            country_ids=None, probabilities=None, suffix=''):
        """ Helper tool method creating a batch of leads, useful when dealing
        with batch processes. Please update me.

        :param string type: 'lead', 'opportunity', 'mixed' (lead then opp),
          None (depends on configuration);
        :param partner_count: if not partner_ids is given, generate partner count
          customers; other leads will have no customer;
        :param partner_ids: a set of partner ids to cycle when creating leads;
        :param user_ids: a set of user ids to cycle when creating leads;

        :return: create leads
        """
        types = ['lead', 'opportunity']
        leads_data = [{
            'name': f'TestLead{suffix}_{x:04d}',
            'type': lead_type if lead_type else types[x % 2],
            'priority': '%s' % (x % 3),
        } for x in range(count)]

        # generate customer information
        partners = []
        if partner_count:
            partners = self.env['res.partner'].create([{
                'name': 'AutoPartner_%04d' % (x),
                'email': tools.formataddr((
                    'AutoPartner_%04d' % (x),
                    'partner_email_%04d@example.com' % (x),
                )),
            } for x in range(partner_count)])

        # customer information
        if partner_ids:
            for idx, lead_data in enumerate(leads_data):
                lead_data['partner_id'] = partner_ids[idx % len(partner_ids)]
        else:
            for idx, lead_data in enumerate(leads_data):
                if partner_count and idx < partner_count:
                    lead_data['partner_id'] = partners[idx].id
                else:
                    lead_data['email_from'] = tools.formataddr((
                        'TestCustomer_%02d' % (idx),
                        'customer_email_%04d@example.com' % (idx)
                    ))

        # country + phone information
        if country_ids:
            cid_to_country = dict(
                (country.id, country)
                for country in self.env['res.country'].browse([cid for cid in country_ids if cid])
            )
            for idx, lead_data in enumerate(leads_data):
                country_id = country_ids[idx % len(country_ids)]
                country = cid_to_country.get(country_id, self.env['res.country'])
                lead_data['country_id'] = country.id
                if lead_data['country_id']:
                    lead_data['phone'] = phone_validation.phone_format(
                        '0456%04d99' % (idx),
                        country.code, country.phone_code,
                        force_format='E164')
                else:
                    lead_data['phone'] = '+32456%04d99' % (idx)

        # salesteam information
        if user_ids:
            for idx, lead_data in enumerate(leads_data):
                lead_data['user_id'] = user_ids[idx % len(user_ids)]

        # probabilities
        if probabilities:
            for idx, lead_data in enumerate(leads_data):
                lead_data['probability'] = probabilities[idx % len(probabilities)]

        # duplicates (currently only with email)
        dups_data = []
        if email_dup_count and not partner_ids:
            for idx, lead_data in enumerate(leads_data):
                if not lead_data.get('partner_id') and lead_data['email_from']:
                    dup_data = dict(lead_data)
                    dup_data['name'] = 'Duplicated-%s' % dup_data['name']
                    dups_data.append(dup_data)
                if len(dups_data) >= email_dup_count:
                    break

        return self.env['crm.lead'].create(leads_data + dups_data)

    def _create_duplicates(self, lead, create_opp=True):
        """ Helper tool method creating, based on a given lead

          * a customer (res.partner) based on lead email (to test partner finding)
            -> FIXME: using same normalized email does not work currently, only exact email works
          * a lead with same email_from
          * a lead with same email_normalized (other email_from)
          * a lead with customer but another email
          * a lost opportunity with same email_from
        """
        customer = self.env['res.partner'].create({
            'name': 'Lead1 Email Customer',
            'email': lead.email_from,
        })
        lead_email_from = self.env['crm.lead'].create({
            'name': 'Duplicate: same email_from',
            'type': 'lead',
            'team_id': lead.team_id.id,
            'email_from': lead.email_from,
            'probability': lead.probability,
        })
        lead_email_normalized = self.env['crm.lead'].create({
            'name': 'Duplicate: email_normalize comparison',
            'type': 'lead',
            'team_id': lead.team_id.id,
            'stage_id': lead.stage_id.id,
            'email_from': 'CUSTOMER WITH NAME <%s>' % lead.email_normalized.upper(),
            'probability': lead.probability,
        })
        lead_partner = self.env['crm.lead'].create({
            'name': 'Duplicate: customer ID',
            'type': 'lead',
            'team_id': lead.team_id.id,
            'partner_id': customer.id,
            'probability': lead.probability,
        })
        if create_opp:
            opp_lost = self.env['crm.lead'].create({
                'name': 'Duplicate: lost opportunity',
                'type': 'opportunity',
                'team_id': lead.team_id.id,
                'stage_id': lead.stage_id.id,
                'email_from': lead.email_from,
                'probability': lead.probability,
            })
            opp_lost.action_set_lost()
        else:
            opp_lost = self.env['crm.lead']

        new_leads = lead_email_from + lead_email_normalized + lead_partner + opp_lost
        new_leads.flush_recordset()  # compute notably probability
        return customer, new_leads

    @contextmanager
    def assertLeadMerged(self, opportunity, leads, **expected):
        """ Assert result of lead _merge_opportunity process. This is done using
        a context manager in order to save original opportunity (master lead)
        values. Indeed those will be modified during merge process. We have to
        ensure final values are correct taking into account all leads values
        before merging them.

        :param opportunity: final opportunity
        :param leads: merged leads (including opportunity)
        """
        self.assertIn(opportunity, leads)

        # save opportunity value before being modified by merge process
        fields_all = self.FIELDS_FIRST_SET + self.merge_fields
        original_opp_values = dict(
            (fname, opportunity[fname])
            for fname in fields_all
            if fname in opportunity
        )

        def _find_value(lead, fname):
            if lead == opportunity:
                return original_opp_values[fname]
            return lead[fname]

        def _first_set(fname):
            values = [_find_value(lead, fname) for lead in leads]
            return next((value for value in values if value), False)

        def _get_type():
            values = [_find_value(lead, 'type') for lead in leads]
            return 'opportunity' if 'opportunity' in values else 'lead'

        def _get_description():
            values = [_find_value(lead, 'description') for lead in leads]
            return '<br><br>'.join(value for value in values if value)

        def _get_priority():
            values = [_find_value(lead, 'priority') for lead in leads]
            return max(values)

        def _aggregate(fname):
            if isinstance(self.env['crm.lead'][fname], models.BaseModel):
                values = leads.mapped(fname)
            else:
                values = [_find_value(lead, fname) for lead in leads]
            return values

        try:
            # merge process will modify opportunity
            yield
        finally:
            # support specific values caller may want to check in addition to generic tests
            for fname, expected in expected.items():
                if expected is False:
                    self.assertFalse(opportunity[fname], "%s must be False" % fname)
                else:
                    self.assertEqual(opportunity[fname], expected, "%s must be equal to %s" % (fname, expected))

            # classic fields: first not void wins or specific computation
            for fname in fields_all:
                if fname not in opportunity:  # not all fields available when doing -u
                    continue
                opp_value = opportunity[fname]
                if fname == 'description':
                    self.assertEqual(opp_value, _get_description())
                elif fname == 'type':
                    self.assertEqual(opp_value, _get_type())
                elif fname == 'priority':
                    self.assertEqual(opp_value, _get_priority())
                elif fname in ('order_ids', 'visitor_ids'):
                    self.assertEqual(opp_value, _aggregate(fname))
                elif fname in PARTNER_ADDRESS_FIELDS_TO_SYNC:
                    # Specific computation, has its own test
                    continue
                else:
                    self.assertEqual(
                        opp_value if opp_value or not isinstance(opp_value, models.BaseModel) else False,
                        _first_set(fname)
                    )


class TestLeadConvertCommon(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertCommon, cls).setUpClass()
        # Sales Team organization
        # Role: M (team member) R (team manager)
        # SALESMAN---------------sales_team_1-----sales_team_convert
        # admin------------------M----------------/  (sales_team_1_m2)
        # user_sales_manager-----R----------------R
        # user_sales_leads-------M----------------/  (sales_team_1_m1)
        # user_sales_salesman----/----------------M  (sales_team_convert_m1)

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
            'assignment_domain': [('priority', 'in', ['1', '2', '3'])],
        })
        cls.sales_team_convert_m1 = cls.env['crm.team.member'].create({
            'user_id': cls.user_sales_salesman.id,
            'crm_team_id': cls.sales_team_convert.id,
            'assignment_max': 30,
            'assignment_domain': False,
        })
        cls.stage_team_convert_1 = cls.env['crm.stage'].create({
            'name': 'New',
            'sequence': 1,
            'team_id': cls.sales_team_convert.id,
        })

        cls.lead_1.write({'date_open': Datetime.from_string('2020-01-15 11:30:00')})

        cls.crm_lead_dt_patcher = patch('odoo.addons.crm.models.crm_lead.fields.Datetime', wraps=Datetime)
        cls.crm_lead_dt_mock = cls.startClassPatcher(cls.crm_lead_dt_patcher)

    @classmethod
    def _switch_to_multi_membership(cls):
        # Sales Team organization
        # Role: M (team member) R (team manager)
        # SALESMAN---------------sales_team_1-----sales_team_convert
        # admin------------------M----------------/    (sales_team_1_m2)
        # user_sales_manager-----R----------------R+M  <-- NEW (sales_team_convert_m2)
        # user_sales_leads-------M----------------/    (sales_team_1_m1)
        # user_sales_salesman----M----------------M    <-- NEW (sales_team_1_m3 / sales_team_convert_m1)

        # SALESMAN--------------sales_team----------assign_max
        # admin-----------------sales_team_1--------15 (tot: 0.5/day)
        # user_sales_manager----sales_team_convert--60 (tot: 2/day)
        # user_sales_leads------sales_team_1--------45 (tot: 1.5/day)
        # user_sales_salesman---sales_team_1--------15 (tot: 1.5/day)
        # user_sales_salesman---sales_team_convert--30

        cls.sales_team_1_m1.write({
            'assignment_max': 45,
            'assignment_domain': False,
        })
        cls.sales_team_1_m2.write({
            'assignment_max': 15,
            'assignment_domain': [('probability', '>=', 10)],
        })

        cls.env['ir.config_parameter'].set_param('sales_team.membership_multi', True)
        cls.sales_team_1_m3 = cls.env['crm.team.member'].create({
            'user_id': cls.user_sales_salesman.id,
            'crm_team_id': cls.sales_team_1.id,
            'assignment_max': 15,
            'assignment_domain': [('probability', '>=', 20)],
        })
        cls.sales_team_convert_m1.write({
            'assignment_max': 30,
            'assignment_domain': [('probability', '>=', 20)]
        })
        cls.sales_team_convert_m2 = cls.env['crm.team.member'].create({
            'user_id': cls.user_sales_manager.id,
            'crm_team_id': cls.sales_team_convert.id,
            'assignment_max': 60,
            'assignment_domain': False,
        })

    @classmethod
    def _switch_to_auto_assign(cls):
        cls.env['ir.config_parameter'].set_param('crm.lead.auto.assignment', True)
        cls.assign_cron = cls.env.ref('crm.ir_cron_crm_lead_assign')
        cls.assign_cron.update({
            'active': True,
            'interval_type':  'days',
            'interval_number': 1,
        })

    def assertMemberAssign(self, member, count):
        """ Check assign result and that domains are effectively taken into account """
        self.assertEqual(member.lead_day_count, count)
        member_leads = self.env['crm.lead'].search([
            ('user_id', '=', member.user_id.id),
            ('team_id', '=', member.crm_team_id.id),
            ('date_open', '>=', Datetime.now() - timedelta(hours=24)),
        ])
        self.assertEqual(len(member_leads), count)
        if member.assignment_domain:
            self.assertEqual(
                member_leads.filtered_domain(literal_eval(member.assignment_domain)),
                member_leads
            )
        # TODO this condition is not fulfilled in case of merge, need to change merge/assignment process
        # if member.crm_team_id.assignment_domain:
        #     self.assertEqual(
        #         member_leads.filtered_domain(literal_eval(member.crm_team_id.assignment_domain)),
        #         member_leads,
        #         'Assign domain not matching: %s' % member.crm_team_id.assignment_domain
        #     )

class TestLeadConvertMassCommon(TestLeadConvertCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertMassCommon, cls).setUpClass()
        # Sales Team organization
        # Role: M (team member) R (team manager)
        # SALESMAN-------------------sales_team_1-----sales_team_convert
        # admin----------------------M----------------/  (sales_team_1_m2)
        # user_sales_manager---------R----------------R  (sales_team_1_m1)
        # user_sales_leads-----------M----------------/
        # user_sales_leads_convert---/----------------M  <-- NEW (sales_team_convert_m2)
        # user_sales_salesman--------/----------------M  (sales_team_convert_m1)

        cls.user_sales_leads_convert = mail_new_test_user(
            cls.env, login='user_sales_leads_convert',
            name='Lucien Sales Leads Convert', email='crm_leads_2@test.example.com',
            company_id=cls.env.ref("base.main_company").id,
            notification_type='inbox',
            groups='sales_team.group_sale_salesman_all_leads,base.group_partner_manager,crm.group_use_lead',
        )
        cls.sales_team_convert_m2 = cls.env['crm.team.member'].create({
            'user_id': cls.user_sales_leads_convert.id,
            'crm_team_id': cls.sales_team_convert.id,
        })

        cls.lead_w_partner = cls.env['crm.lead'].create({
            'name': 'New1',
            'type': 'lead',
            'priority': '0',
            'probability': 10,
            'user_id': cls.user_sales_manager.id,
            'stage_id': False,
            'partner_id': cls.contact_1.id,
        })
        cls.lead_w_partner.write({'stage_id': False})

        cls.tags = cls.env['crm.tag'].create([{'name': 'Tag %i' % i} for i in range(4)])
        cls.lead_1.tag_ids = cls.tags[:3]
        cls.lead_w_partner_company = cls.env['crm.lead'].create({
            'name': 'New1',
            'type': 'lead',
            'probability': 50,
            'user_id': cls.user_sales_manager.id,
            'stage_id': cls.stage_team1_1.id,
            'partner_id': cls.contact_company_1.id,
            'contact_name': 'Hermes Conrad',
            'email_from': 'hermes.conrad@test.example.com',
            'tag_ids': (cls.tags[:2] | cls.tags[3]),
        })
        cls.lead_w_contact = cls.env['crm.lead'].create({
            'name': 'LeadContact',
            'type': 'lead',
            'probability': 25,
            'contact_name': 'TestContact',
            'user_id': cls.user_sales_salesman.id,
            'stage_id': cls.stage_gen_1.id,
        })
        cls.lead_w_email = cls.env['crm.lead'].create({
            'name': 'LeadEmailAsContact',
            'type': 'lead',
            'priority': '2',
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
        cls.env.flush_all()
