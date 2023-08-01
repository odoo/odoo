# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCase):

    def test_01_crm_tour(self):
        self.start_tour("/web", 'crm_tour', login="admin")

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
        self.start_tour("/web", 'crm_rainbowman', login="temp_crm_user")

    def test_03_crm_tour_forecast(self):
        self.start_tour("/web", 'crm_forecast', login="admin")

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

        self.start_tour('/web', 'crm_email_and_phone_propagation_edit_save', login='admin')

        self.assertEqual(lead.email_from, 'test@example.com', 'Should not have changed the lead email')
        self.assertEqual(lead.phone, '+32 494 44 44 44', 'Should not have changed the lead phone')
        self.assertEqual(partner.email, 'test@example.com', 'Should have propagated the lead email on the partner')
        self.assertEqual(partner.phone, '+32 494 44 44 44', 'Should have propagated the lead phone on the partner')

    def test_email_and_phone_propagation_remove_email_and_phone(self):
        """Test the propagation of the email / phone on the partner.

        If we remove the email and phone on the lead, it should be removed on the
        partner. This test check that we correctly detect field values changes in JS
        (aka undefined VS falsy).
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

        # Check initial state
        self.assertEqual(partner.email, 'test@example.com')
        self.assertEqual(lead.phone, '+32 494 44 44 44')
        self.assertEqual(lead.email_from, 'test@example.com')
        self.assertEqual(lead.phone, '+32 494 44 44 44')

        self.assertFalse(lead.partner_email_update)
        self.assertFalse(lead.partner_phone_update)

        self.start_tour('/web', 'crm_email_and_phone_propagation_remove_email_and_phone', login='admin')

        self.assertFalse(lead.email_from, 'Should have removed the email')
        self.assertFalse(lead.phone, 'Should have removed the phone')
        self.assertFalse(partner.email, 'Should have removed the email')
        self.assertFalse(partner.phone, 'Should have removed the phone')
