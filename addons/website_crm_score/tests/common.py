from openerp.tests import common


class TestScoring(common.TransactionCase):

    def _init_(self):
        pass
        # self._build_email_args_list = []
        # self._build_email_kwargs_list = []

    def setUp(self):
        super(TestScoring, self).setUp()
        cr, uid = self.cr, self.uid

        # empty tables before testing to only use test records
        cr.execute("""
                UPDATE res_partner SET section_id=NULL;
        """)
        cr.execute("""
                TRUNCATE TABLE section_user;
        """)
        cr.execute("""
                DELETE FROM crm_case_section;
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
        self.leads_dry_run = self.registry('leads.dry.run')
        self.pageview = self.registry('website.crm.pageview')
        self.website_crm_score = self.registry('website.crm.score')
        self.section = self.registry('crm.case.section')
        self.res_users = self.registry('res.users')
        self.section_user = self.registry('section.user')
        self.country = self.registry('res.country')
        self.crm_case_stage = self.registry('crm.case.stage')

        self.belgium = self.country.search(cr, uid, [('name', '=', 'Belgium')])[0]
        self.france = self.country.search(cr, uid, [('name', '=', 'France')])[0]

        self.stage = self.crm_case_stage.create(cr, uid, {
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
            'stage_id': self.stage,

        })
        self.lead1 = self.crm_lead.create(cr, uid, {
            'name': 'lead1',
            'country_id': self.france,
            'email_from': 'lead1@test.com',
            'user_id': None,
            'stage_id': self.stage,
        })
        self.lead2 = self.crm_lead.create(cr, uid, {
            'name': 'lead2',
            'email_from': 'lead2@test.com',
            'user_id': None,
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
        self.section0 = self.section.create(cr, uid, {
            'name': 'section0',
            'code': 'S0',
            'score_section_domain': [('country_id', '=', 'Belgium')],
        })
        self.section1 = self.section.create(cr, uid, {
            'name': 'section1',
            'code': 'S1',
            'score_section_domain': [('country_id', '=', 'France')],
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

        # Section_user
        self.section_user0 = self.section_user.create(cr, uid, {
            'user_id': self.salesmen0,
            'section_id': self.section0,
            'maximum_user_leads': 1,
            'section_user_domain': [('country_id', '=', 'Belgium')],
        })
        self.section_user1 = self.section_user.create(cr, uid, {
            'user_id': self.salesmen1,
            'section_id': self.section0,
            'maximum_user_leads': 0,
            'section_user_domain': [('country_id', '=', 'France')],
        })
        self.section_user2 = self.section_user.create(cr, uid, {
            'user_id': self.salesmen1,
            'section_id': self.section1,
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
