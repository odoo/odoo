# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os

from unittest import skipIf

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests import HttpCase
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCase, TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.user_admin').tour_enabled = False

    def test_01_crm_tour(self):
        # TODO: The tour is raising a JS error when selecting Brandon Freeman
        # but with the demo data it succeeds to continue if there is already another lead
        # in the pipe. Then the tour is using a record in the Qualified stage to create
        # an activity, which is not existing without demo data as well
        brandon = self.env["res.partner"].create({
            'name': 'Brandon Freeman',
            'email': 'brandon.freeman55@example.com',
            'phone': '(355)-687-3262',
        })
        self.env['crm.lead'].create([{
            'name': "Zizizbroken",
            'type': 'opportunity',
            'partner_id': brandon.id,
            'stage_id': self.stage_team1_1.id,
            'user_id': self.env.ref('base.user_admin').id,
        }, {
            'name': "Zizizbroken 2",
            'type': 'opportunity',
            'partner_id': brandon.id,
            'stage_id': self.stage_gen_1.id,
            'user_id': self.env.ref('base.user_admin').id,
        }])
        self.start_tour("/odoo", 'crm_tour', login="admin")

    @skipIf(os.getenv("ODOO_FAKETIME_TEST_MODE"), 'This tour uses CURRENT_DATE which cannot work in faketime mode')
    def test_02_crm_tour_rainbowman(self):
        # we create a new user to make sure they get the 'Congrats on your first deal!'
        # rainbowman message.
        self.env['res.users'].create({
            'name': 'Temporary CRM User',
            'login': 'temp_crm_user',
            'password': 'temp_crm_user',
            'groups_id': [(6, 0, [
                    self.ref('base.group_user'),
                    self.ref('sales_team.group_sale_salesman')
                ])]
        })
        self.start_tour("/odoo", 'crm_rainbowman', login="temp_crm_user")

    def test_03_crm_tour_forecast(self):
        self.start_tour("/odoo", 'crm_forecast', login="admin")

    def test_email_and_phone_propagation_edit_save(self):
        """Test the propagation of the email / phone on the partner.

        If the partner has no email but the lead has one, it should be propagated
        if we edit and save the lead form.
        """
        self.env['crm.lead'].search([]).unlink()
        user_admin = self.env['res.users'].search([('login', '=', 'admin')])

        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        lead = self.env['crm.lead'].create({
            'name': 'Test Lead Propagation',
            'type': 'opportunity',
            'user_id': user_admin.id,
            'partner_id': partner.id,
            'email_from': 'test@example.com',
            'phone': '+32 494 44 44 44',
        })
        partner.email = False
        partner.phone = False

        # Check initial state
        self.assertFalse(partner.email)
        self.assertFalse(partner.phone)
        self.assertEqual(lead.email_from, 'test@example.com')
        self.assertEqual(lead.phone, '+32 494 44 44 44')

        self.assertTrue(lead.partner_email_update)
        self.assertTrue(lead.partner_phone_update)

        self.start_tour('/odoo', 'crm_email_and_phone_propagation_edit_save', login='admin')

        self.assertEqual(lead.email_from, 'test@example.com', 'Should not have changed the lead email')
        self.assertEqual(lead.phone, '+32 494 44 44 44', 'Should not have changed the lead phone')
        self.assertEqual(partner.email, 'test@example.com', 'Should have propagated the lead email on the partner')
        self.assertEqual(partner.phone, '+32 494 44 44 44', 'Should have propagated the lead phone on the partner')
