# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.crm.tests import common as crm_common
from odoo.fields import Command
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadConvertToTicket(crm_common.TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertToTicket, cls).setUpClass()
        cls.lead_1.write({
            'user_id': cls.user_sales_salesman.id,
        })

    @users('user_sales_salesman')
    def test_lead_convert_to_quotation_create(self):
        """ Test partner creation while converting """
        # Perform initial tests, do not repeat them at each test
        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.partner_id, self.env['res.partner'])
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'amy.wong@test.example.com')])
        self.assertEqual(new_partner, self.env['res.partner'])

        # invoke wizard and apply it
        convert = self.env['crm.quotation.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id
        }).create({})

        self.assertEqual(convert.action, 'create')
        self.assertEqual(convert.partner_id, self.env['res.partner'])

        action = convert.action_apply()

        # test lead update
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'amy.wong@test.example.com')])
        self.assertEqual(lead.partner_id, new_partner)

        # test wizard action (does not create anything, just returns action)
        self.assertEqual(action['res_model'], 'sale.order')
        self.assertEqual(action['context']['default_partner_id'], new_partner.id)

    @users('user_sales_salesman')
    def test_lead_convert_to_quotation_exist(self):
        """ Test taking only existing customer while converting """
        lead = self.lead_1.with_user(self.env.user)

        # invoke wizard and apply it
        convert = self.env['crm.quotation.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id
        }).create({'action': 'exist'})

        self.assertEqual(convert.action, 'exist')
        self.assertEqual(convert.partner_id, self.env['res.partner'])

        action = convert.action_apply()

        # test lead update
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'amy.wong@test.example.com')])
        self.assertEqual(new_partner, self.env['res.partner'])

        convert.write({'partner_id': self.contact_2.id})
        action = convert.action_apply()

        # test lead update
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'amy.wong@test.example.com')])
        self.assertEqual(new_partner, self.env['res.partner'])
        self.assertEqual(lead.partner_id, self.contact_2)
        # TDE TODO: have a real sync assert for lead / contact
        self.assertEqual(lead.email_from, self.contact_2.email)
        self.assertEqual(lead.mobile, self.contact_2.mobile)
        self.assertEqual(action['context']['default_partner_id'], self.contact_2.id)

    @users('user_sales_salesman')
    def test_lead_convert_to_quotation_false_match_create(self):
        lead = self.lead_1.with_user(self.env.user)

        # invoke wizard and apply it
        convert = self.env['crm.quotation.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id,
        }).create({'action': 'create'})

        convert.write({'partner_id': self.contact_2.id})

        self.assertEqual(convert.action, 'create')

        # ignore matching partner and create a new one
        convert.action_apply()

        self.assertTrue(bool(lead.partner_id.id))
        self.assertNotEqual(lead.partner_id, self.contact_2)

    @users('user_sales_salesman')
    def test_lead_convert_to_quotation_nothing(self):
        """ Test doing nothing about customer while converting """
        lead = self.lead_1.with_user(self.env.user)

        # invoke wizard and apply it
        convert = self.env['crm.quotation.partner'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id,
            'default_action': 'nothing',
        }).create({})

        self.assertEqual(convert.action, 'nothing')
        self.assertEqual(convert.partner_id, self.env['res.partner'])

        action = convert.action_apply()

        # test lead update
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'amy.wong@test.example.com')])
        self.assertEqual(new_partner, self.env['res.partner'])
        self.assertEqual(lead.partner_id, self.env['res.partner'])
        self.assertEqual(action['context']['default_partner_id'], False)

    def test_crm_quotation_expected_revenue(self):
        """ Test the updation of the expected_revenue when the quotation is sent.
        If the expected_revenue of the lead is smaller than the total of each quote, update it to the total of the lowest quote.
        e.g.
        lead = 40$
        q1 = 45$, q2 = 98$, q3 = 73$
        ===> The lead would be updated, from 40 to 45$
        """
        product1, product2 = self.env['product.template'].create([{
            'name': 'Test product1',
            'list_price': 100.0,
        }, {
            'name': 'Test product2',
            'list_price': 200.0,
        }])

        so1 = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'opportunity_id': self.lead_1.id,
            'order_line': [
                Command.create({
                    'product_id': product1.product_variant_id.id,
                }),
            ],
        })

        email_act = so1.action_quotation_send()
        email_ctx = email_act.get('context', {})
        so1.with_context(**email_ctx).message_post_with_source(
            self.env['mail.template'].browse(email_ctx.get('default_template_id')),
            subtype_xmlid='mail.mt_comment',
        )
        self.assertEqual(self.lead_1.expected_revenue, 100)
        so1.action_confirm()

        so2 = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'opportunity_id': self.lead_1.id,
            'order_line': [
                Command.create({
                    'product_id': product1.product_variant_id.id,
                }),
                Command.create({
                    'product_id': product2.product_variant_id.id,
                }),
            ],
        })

        email_act = so2.action_quotation_send()
        email_ctx = email_act.get('context', {})
        so2.with_context(**email_ctx).message_post_with_source(
            self.env['mail.template'].browse(email_ctx.get('default_template_id')),
            subtype_xmlid='mail.mt_comment',
        )
        self.assertEqual(self.lead_1.expected_revenue, 300)
