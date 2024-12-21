# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests import common as crm_common
from odoo.tests.common import tagged, users


@tagged('lead_manage', 'crm_performance', 'post_install', '-at_install')
class TestLeadConvertMass(crm_common.TestLeadConvertMassCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertMass, cls).setUpClass()

        cls.leads = cls.lead_1 + cls.lead_w_partner + cls.lead_w_email_lost
        cls.assign_users = cls.user_sales_manager + cls.user_sales_leads_convert + cls.user_sales_salesman

    @users('user_sales_manager')
    def test_assignment_salesmen(self):
        test_leads = self._create_leads_batch(count=50, user_ids=[False])
        user_ids = self.assign_users.ids
        self.assertEqual(test_leads.user_id, self.env['res.users'])

        with self.assertQueryCount(user_sales_manager=0):
            test_leads = self.env['crm.lead'].browse(test_leads.ids)

        with self.assertQueryCount(user_sales_manager=471):  # crm 605 / com 605 / ent 605
            test_leads._handle_salesmen_assignment(user_ids=user_ids, team_id=False)

        self.assertEqual(test_leads.team_id, self.sales_team_convert | self.sales_team_1)
        self.assertEqual(test_leads[0::3].user_id, self.user_sales_manager)
        self.assertEqual(test_leads[1::3].user_id, self.user_sales_leads_convert)
        self.assertEqual(test_leads[2::3].user_id, self.user_sales_salesman)

    @users('user_sales_manager')
    def test_assignment_salesmen_wteam(self):
        test_leads = self._create_leads_batch(count=50, user_ids=[False])
        user_ids = self.assign_users.ids
        team_id = self.sales_team_convert.id
        self.assertEqual(test_leads.user_id, self.env['res.users'])

        with self.assertQueryCount(user_sales_manager=0):
            test_leads = self.env['crm.lead'].browse(test_leads.ids)

        with self.assertQueryCount(user_sales_manager=449):  # crm 543 / com 545 / ent 584
            test_leads._handle_salesmen_assignment(user_ids=user_ids, team_id=team_id)

        self.assertEqual(test_leads.team_id, self.sales_team_convert)
        self.assertEqual(test_leads[0::3].user_id, self.user_sales_manager)
        self.assertEqual(test_leads[1::3].user_id, self.user_sales_leads_convert)
        self.assertEqual(test_leads[2::3].user_id, self.user_sales_salesman)

    @users('user_sales_manager')
    def test_mass_convert_internals(self):
        """ Test internals mass converted in convert mode, without duplicate management """
        # reset some assigned users to test salesmen assign
        (self.lead_w_partner | self.lead_w_email_lost).write({
            'user_id': False
        })

        mass_convert = self.env['crm.lead2opportunity.partner.mass'].with_context({
            'active_model': 'crm.lead',
            'active_ids': self.leads.ids,
            'active_id': self.leads.ids[0]
        }).create({
            'deduplicate': False,
            'user_id': self.user_sales_salesman.id,
            'force_assignment': False,
        })

        # default values
        self.assertEqual(mass_convert.name, 'convert')
        self.assertEqual(mass_convert.action, 'each_exist_or_create')
        # depending on options
        self.assertEqual(mass_convert.partner_id, self.env['res.partner'])
        self.assertEqual(mass_convert.deduplicate, False)
        self.assertEqual(mass_convert.user_id, self.user_sales_salesman)
        self.assertEqual(mass_convert.team_id, self.sales_team_convert)

        mass_convert.action_mass_convert()
        for lead in self.lead_1 | self.lead_w_partner:
            self.assertEqual(lead.type, 'opportunity')
            if lead == self.lead_w_partner:
                self.assertEqual(lead.user_id, self.env['res.users'])  # user_id is bypassed
                self.assertEqual(lead.partner_id, self.contact_1)
            elif lead == self.lead_1:
                self.assertEqual(lead.user_id, self.user_sales_leads)  # existing value not forced
                new_partner = lead.partner_id
                self.assertEqual(new_partner.name, 'Amy Wong')
                self.assertEqual(new_partner.email, 'amy.wong@test.example.com')

        # test unforced assignation
        mass_convert.write({
            'user_ids': self.user_sales_salesman.ids,
        })
        mass_convert.action_mass_convert()
        self.assertEqual(self.lead_w_partner.user_id, self.user_sales_salesman)
        self.assertEqual(self.lead_1.user_id, self.user_sales_leads)  # existing value not forced

        # lost leads are untouched
        self.assertEqual(self.lead_w_email_lost.type, 'lead')
        self.assertFalse(self.lead_w_email_lost.active)
        self.assertFalse(self.lead_w_email_lost.date_conversion)
        # TDE FIXME: partner creation is done even on lost leads because not checked in wizard
        # self.assertEqual(self.lead_w_email_lost.partner_id, self.env['res.partner'])

    @users('user_sales_manager')
    def test_mass_convert_deduplicate(self):
        """ Test duplicated_lead_ids fields having another behavior in mass convert
        because why not. Its use is: among leads under convert, store those with
        duplicates if deduplicate is set to True. """
        _customer, lead_1_dups = self._create_duplicates(self.lead_1, create_opp=False)
        lead_1_final = self.lead_1  # after merge: same but with lower ID

        _customer2, lead_w_partner_dups = self._create_duplicates(self.lead_w_partner, create_opp=False)
        lead_w_partner_final = lead_w_partner_dups[0]  # lead_w_partner has no stage -> lower in sort by confidence
        lead_w_partner_dups_partner = lead_w_partner_dups[1]  # copy with a partner_id (with the same email)

        mass_convert = self.env['crm.lead2opportunity.partner.mass'].with_context({
            'active_model': 'crm.lead',
            'active_ids': self.leads.ids,
        }).create({
            'deduplicate': True,
        })
        self.assertEqual(mass_convert.action, 'each_exist_or_create')
        self.assertEqual(mass_convert.name, 'convert')
        self.assertEqual(mass_convert.lead_tomerge_ids, self.leads)
        self.assertEqual(mass_convert.duplicated_lead_ids, self.lead_1 | self.lead_w_partner)

        mass_convert.action_mass_convert()

        self.assertEqual(
            (lead_1_dups | lead_w_partner_dups | lead_w_partner_dups_partner).exists(),
            lead_w_partner_final
        )
        for lead in lead_1_final | lead_w_partner_final:
            self.assertTrue(lead.active)
            self.assertEqual(lead.type, 'opportunity')

    @users('user_sales_manager')
    def test_mass_convert_find_existing(self):
        """ Check that we don't find a wrong partner
            that have similar name during mass conversion
        """
        wrong_partner = self.env['res.partner'].create({
            'name': 'casa depapel',
            'street': "wrong street"
        })

        lead = self.env['crm.lead'].create({'name': 'Asa Depape'})
        mass_convert = self.env['crm.lead2opportunity.partner.mass'].with_context({
            'active_model': 'crm.lead',
            'active_ids': lead.ids,
            'active_id': lead.ids[0]
        }).create({
            'deduplicate': False,
            'action': 'each_exist_or_create',
            'name': 'convert',
        })
        mass_convert.action_mass_convert()

        self.assertNotEqual(lead.partner_id, wrong_partner, "Partner Id should not match the wrong contact")

    @users('user_sales_manager')
    def test_mass_convert_performances(self):
        test_leads = self._create_leads_batch(count=50, user_ids=[False])
        user_ids = self.assign_users.ids

        # randomness: at least 1 query
        with self.assertQueryCount(user_sales_manager=1435):  # crm 1503 / com 1790 / ent 1800
            mass_convert = self.env['crm.lead2opportunity.partner.mass'].with_context({
                'active_model': 'crm.lead',
                'active_ids': test_leads.ids,
            }).create({
                'deduplicate': True,
                'user_ids': user_ids,
                'force_assignment': True,
            })
            mass_convert.action_mass_convert()

        self.assertEqual(set(test_leads.mapped('type')), set(['opportunity']))
        self.assertEqual(len(test_leads.partner_id), len(test_leads))
        # TDE FIXME: strange
        # self.assertEqual(test_leads.team_id, self.sales_team_convert | self.sales_team_1)
        self.assertEqual(test_leads.team_id, self.sales_team_1)
        self.assertEqual(test_leads[0::3].user_id, self.user_sales_manager)
        self.assertEqual(test_leads[1::3].user_id, self.user_sales_leads_convert)
        self.assertEqual(test_leads[2::3].user_id, self.user_sales_salesman)

    @users('user_sales_manager')
    def test_mass_convert_w_salesmen(self):
        # reset some assigned users to test salesmen assign
        (self.lead_w_partner | self.lead_w_email_lost).write({
            'user_id': False
        })

        mass_convert = self.env['crm.lead2opportunity.partner.mass'].with_context({
            'active_model': 'crm.lead',
            'active_ids': self.leads.ids,
            'active_id': self.leads.ids[0]
        }).create({
            'deduplicate': False,
            'user_ids': self.assign_users.ids,
            'force_assignment': True,
        })

        # TDE FIXME: what happens if we mix people from different sales team ? currently nothing, to check
        mass_convert.action_mass_convert()

        for idx, lead in enumerate(self.leads - self.lead_w_email_lost):
            self.assertEqual(lead.type, 'opportunity')
            assigned_user = self.assign_users[idx % len(self.assign_users)]
            self.assertEqual(lead.user_id, assigned_user)
