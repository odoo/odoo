# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.tests.common import TransactionCase, users
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sales_team.tests.common import TestSalesMC


class TestCornerCases(TransactionCase):

    def setUp(self):
        super(TestCornerCases, self).setUp()
        self.user_sales_leads = mail_new_test_user(
            self.env, login='user_sales_leads',
            name='Laetitia Sales Leads', email='crm_leads@test.example.com',
            company_id=self.env.user.company_id.id,
            notification_type='inbox',
            groups='sales_team.group_sale_salesman_all_leads,base.group_partner_manager',
        )
        self.sales_team_1 = self.env['crm.team'].create({
            'name': 'Test Sales Team',
            'sequence': 5,
            'company_id': False,
            'user_id': self.env.user.id,
        })

    def test_unicity(self):
        """ Archived memberships should be removed when detecting duplicates.
        Creating duplicates should raise unicity constraint.

        Note: redoing the data set to avoid clashing with SavepointCase as
        we expect a db-level assert """
        sales_team_1_m1 = self.env['crm.team.member'].create({
            'user_id': self.user_sales_leads.id,
            'crm_team_id': self.sales_team_1.id,
        })

        sales_team_1_m1.write({'active': False})
        sales_team_1_m1.flush_recordset()

        sales_team_1_m2 = self.env['crm.team.member'].create({
            'user_id': self.user_sales_leads.id,
            'crm_team_id': self.sales_team_1.id,
        })

        found = self.env['crm.team.member'].search([
            ('user_id', '=', self.user_sales_leads.id),
            ('crm_team_id', '=', self.sales_team_1.id),
        ])
        self.assertEqual(found, sales_team_1_m2)

        with self.assertRaises(exceptions.UserError), mute_logger('odoo.sql_db'):
            self.env['crm.team.member'].create({
                'user_id': self.user_sales_leads.id,
                'crm_team_id': self.sales_team_1.id,
            })

    def test_unicity_multicreate(self):
        """ Test constraint works with creating duplicates in the same create
        method. """
        with self.assertRaises(exceptions.UserError), mute_logger('odoo.sql_db'):
            self.env['crm.team.member'].create([
                {'user_id': self.user_sales_leads.id, 'crm_team_id': self.sales_team_1.id},
                {'user_id': self.user_sales_leads.id, 'crm_team_id': self.sales_team_1.id}
            ])


class TestSecurity(TestSalesMC):

    @users('user_sales_leads')
    def test_team_access(self):
        sales_team = self.sales_team_1.with_user(self.env.user)

        sales_team.read(['name'])
        for member in sales_team.member_ids:
            member.read(['name'])

        with self.assertRaises(exceptions.AccessError):
            sales_team.write({'name': 'Trolling'})

        for membership in sales_team.crm_team_member_ids:
            membership.read(['name'])
            with self.assertRaises(exceptions.AccessError):
                membership.write({'active': False})

        with self.assertRaises(exceptions.AccessError):
            sales_team.write({'member_ids': [(5, 0)]})

    @users('user_sales_leads')
    def test_team_multi_company(self):
        self.sales_team_1.with_user(self.env.user).read(['name'])
        with self.assertRaises(exceptions.AccessError):
            self.team_c2.with_user(self.env.user).read(['name'])
