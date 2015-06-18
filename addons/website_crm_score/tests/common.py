# -*- coding: utf-8 -*-
from openerp.tests import common

from mock import Mock


class TestScoring(common.TransactionCase):

    def setUp(self):


        super(TestScoring, self).setUp()
        cr, uid = self.cr, self.uid

        cr.commit = Mock(return_value=None)
        
        # empty tables before testing to only use test records
        cr.execute("""
                UPDATE res_partner SET team_id=NULL;
        """)
        cr.execute("""
                TRUNCATE TABLE team_user;
        """)
        cr.execute("""
                DELETE FROM crm_team;
        """)
        cr.execute("""
                DELETE FROM crm_lead;
        """)
        cr.execute("""
                DELETE FROM website_crm_score;
        """)
        cr.execute("""
                DELETE FROM website_crm_pageview;
        """)

        # Usefull models
        self.crm_lead = self.registry('crm.lead')
        self.crm_leads_dry_run = self.registry('crm.leads.dry.run')
        self.pageview = self.registry('website.crm.pageview')
        self.website_crm_score = self.registry('website.crm.score')
        self.team = self.registry('crm.team')
        self.res_users = self.registry('res.users')
        self.team_user = self.registry('team.user')
        self.country = self.registry('res.country')
        self.crm_stage = self.registry('crm.stage')

        self.belgium = self.country.search(cr, uid, [('name', '=', 'Belgium')])[0]
        self.france = self.country.search(cr, uid, [('name', '=', 'France')])[0]

        self.stage = self.crm_stage.create(cr, uid, {
            'name': 'testing',
            'probability': '50',
            'on_change': False,
        })

        # Lead Data
        self.lead0 = self.crm_lead.create(cr, uid, {
            'name': 'lead0',
            'country_id': self.belgium,
            'email_from': 'lead0@test.com',
            'user_id': None,
            'team_id': False,
            'stage_id': self.stage,

        })
        self.lead1 = self.crm_lead.create(cr, uid, {
            'name': 'lead1',
            'country_id': self.france,
            'email_from': 'lead1@test.com',
            'user_id': None,
            'team_id': False,
            'stage_id': self.stage,
        })
        self.lead2 = self.crm_lead.create(cr, uid, {
            'name': 'lead2',
            'email_from': 'lead2@test.com',
            'user_id': None,
            'team_id': False,
            'stage_id': self.stage,
        })

        # PageView
        self.pageview0 = self.pageview.create(cr, uid, {
            'lead_id': self.lead0,
            'url': 'url0',
        })
        self.pageview0 = self.pageview.create(cr, uid, {
            'lead_id': self.lead1,
            'url': 'url1',
        })

        # Salesteam
        self.team0 = self.team.create(cr, uid, {
            'name': 'team0',
            'code': 'S0',
            'score_team_domain': [('country_id', '=', 'Belgium')],
        })
        self.team1 = self.team.create(cr, uid, {
            'name': 'team1',
            'code': 'S1',
            'score_team_domain': [('country_id', '=', 'France')],
        })

        # Salesmen
        self.salesmen0 = self.res_users.create(cr, uid, {
            'name': 'salesmen0',
            'login': 'salesmen0',
            'alias_name': 'salesmen0',
            'email': 'salesmen0@example.com',
            # 'groups_id': [(6, 0, [self.group_employee_id])]
        }, {'no_reset_password': True})
        self.salesmen1 = self.res_users.create(cr, uid, {
            'name': 'salesmen1',
            'login': 'salesmen1',
            'alias_name': 'salesmen1',
            'email': 'salesmen1@example.com',
            # 'groups_id': [(6, 0, [self.group_employee_id])]
        }, {'no_reset_password': True})

        # team_user
        self.team_user0 = self.team_user.create(cr, uid, {
            'user_id': self.salesmen0,
            'team_id': self.team0,
            'maximum_user_leads': 1,
            'team_user_domain': [('country_id', '=', 'Belgium')],
        })
        self.team_user1 = self.team_user.create(cr, uid, {
            'user_id': self.salesmen1,
            'team_id': self.team0,
            'maximum_user_leads': 0,
            'team_user_domain': [('country_id', '=', 'France')],
        })
        self.team_user2 = self.team_user.create(cr, uid, {
            'user_id': self.salesmen1,
            'team_id': self.team1,
            'maximum_user_leads': 1,
        })

        # Score
        self.score0 = self.website_crm_score.create(cr, uid, {
            'name': 'score0',
            'value': 1000,
            'domain': "[('score_pageview_ids.url', '=', 'url0')]",
        })
        self.score1 = self.website_crm_score.create(cr, uid, {
            'name': 'score1',
            'value': 900,
            'domain': "[('score_pageview_ids.url', '=', 'url1')]",
        })

    def tearDown(self):
        super(TestScoring, self).tearDown()
