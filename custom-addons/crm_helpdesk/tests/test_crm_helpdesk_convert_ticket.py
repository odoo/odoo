# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.crm.tests import common as crm_common
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadConvertToTicket(crm_common.TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadConvertToTicket, cls).setUpClass()
        cls.test_team = cls.env['helpdesk.team'].create({
            'name': 'Test HD Team',
            'stage_ids': [(0, 0, {
                'name': 'New',
                'sequence': 0,
                'template_id': cls.env.ref('helpdesk.new_ticket_request_email_template').id
            })],
        })
        cls.test_ticket_type = cls.env['helpdesk.ticket.type'].create({
            'name': 'Test Type'
        })

        # UTM fields
        cls.test_campaign = cls.env["utm.campaign"].create({
            'name': 'A test UTM campaign',
        })
        cls.test_medium = cls.env["utm.medium"].create({
            'name': 'A test UTM medium'
        })
        cls.test_source = cls.env["utm.source"].create({
            'name': 'A test UTM source'
        })

        cls.lead_1.write({
            'user_id': cls.user_sales_salesman.id,
            'description': 'Lead Description',
            'campaign_id': cls.test_campaign.id,
            'medium_id': cls.test_medium.id,
            'source_id': cls.test_source.id
        })

    def assertTicketLeadConvertData(self, ticket, lead, team, ticket_type, partner):
        # lead update: archived
        self.assertFalse(lead.active)

        # new ticket: data from lead and convert options
        self.assertEqual(ticket.description, lead.description)
        self.assertEqual(ticket.partner_id, partner)
        self.assertEqual(ticket.partner_email, lead.email_from if lead.email_from else partner.email)
        self.assertIn(partner, ticket.message_partner_ids)
        self.assertEqual(ticket.partner_email, lead.email_from if lead.email_from else partner.email)
        self.assertEqual(ticket.partner_phone, lead.phone if lead.phone else partner.phone or lead.mobile or partner.mobile)
        self.assertEqual(ticket.partner_name, partner.name)
        self.assertEqual(ticket.ticket_type_id, ticket_type)
        self.assertFalse(ticket.user_id)
        self.assertEqual(ticket.campaign_id, lead.campaign_id)
        self.assertEqual(ticket.medium_id, lead.medium_id)
        self.assertEqual(ticket.source_id, lead.source_id)

    @users('user_sales_salesman')
    def test_lead_convert_to_ticket_corner_cases(self):
        # admin updates salesman to have helpdesk rights
        self.user_sales_salesman.write({'groups_id': [(4, self.env.ref('helpdesk.group_helpdesk_user').id)]})
        lead = self.lead_1.with_user(self.env.user)

        # invoke wizard and apply it
        convert = self.env['crm.lead.convert2ticket'].with_context({
            'active_model': 'crm.lead',
            'active_id': lead.id
        }).create({
            'team_id': self.test_team.id,
            'ticket_type_id': self.test_ticket_type.id
        })
        action = convert.action_lead_to_helpdesk_ticket()

        # salesmen with helpdesk rights redirected to ticket
        ticket = self.env['helpdesk.ticket'].search([('name', '=', lead.name)])
        self.assertEqual(action['res_model'], ticket._name)

        # admin remove rights on salesman
        lead.write({'active': True})
        self.user_sales_salesman.write({'groups_id': [(3, self.env.ref('sales_team.group_sale_salesman').id)]})

        # sneaky monkey tries to invoke the wizard
        with self.assertRaises(AccessError):
            convert = self.env['crm.lead.convert2ticket'].with_context({
                'active_model': 'crm.lead',
                'active_id': self.lead_1.id
            }).create({
                'team_id': self.test_team.id,
                'ticket_type_id': self.test_ticket_type.id
            })

    @users('user_sales_salesman')
    def test_lead_convert_to_ticket_w_email_rights(self):
        """ Base test for ticket convertion: internal details, based on email """
        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.partner_id, self.env['res.partner'])
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'amy.wong@test.example.com')])
        self.assertEqual(new_partner, self.env['res.partner'])
        msg = lead.message_post(body='Youplaboum', subtype_xmlid='mail.mt_comment', message_type='comment')
        lead_message_ids = lead.message_ids

        # ensure basic rights on team and ticket type
        test_team = self.env['helpdesk.team'].search([('id', '=', self.test_team.id)])
        test_ticket_type = self.env['helpdesk.ticket.type'].search([('id', '=', self.test_ticket_type.id)])

        # invoke wizard and apply it
        convert = self.env['crm.lead.convert2ticket'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id
        }).create({
            'team_id': test_team.id,
            'ticket_type_id': test_ticket_type.id
        })
        action = convert.action_lead_to_helpdesk_ticket()

        # salesmen redirected to ticket
        self.assertEqual(action['res_model'], 'helpdesk.ticket')

        # check created ticket coherency
        ticket = self.env['helpdesk.ticket'].sudo().search([('name', '=', lead.name)])
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'amy.wong@test.example.com')])
        self.assertTrue(len(new_partner), 1)
        self.assertTicketLeadConvertData(ticket, lead, test_team, test_ticket_type, new_partner)

        # check discussion thread transfer
        self.assertTrue(all(message in ticket.message_ids for message in lead_message_ids))
        self.assertIn(msg, ticket.message_ids)

    @users('user_sales_salesman')
    def test_lead_convert_to_ticket_w_name(self):
        lead = self.lead_1.with_user(self.env.user)
        lead.write({
            'name': 'planet EX',
            'email_from': False,
            'contact_name': False,
        })
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # invoke wizard and apply it
        convert = self.env['crm.lead.convert2ticket'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id
        }).create({
            'team_id': self.test_team.id,
            'ticket_type_id': self.test_ticket_type.id
        })
        convert.action_lead_to_helpdesk_ticket()

        # check created ticket coherency
        ticket = self.env['helpdesk.ticket'].sudo().search([('name', '=', lead.name)])
        self.assertTicketLeadConvertData(ticket, lead, self.test_team, self.test_ticket_type, self.contact_company_1)

    @users('user_sales_salesman')
    def test_lead_convert_to_ticket_w_partner(self):
        lead = self.lead_1.with_user(self.env.user)
        lead.write({
            'partner_id': self.contact_1.id,
        })
        # ensure partner updated lead information
        self.assertEqual(lead.partner_id, self.contact_1)
        self.assertEqual(lead.email_from, self.contact_1.email)
        self.assertEqual(lead.partner_name, self.contact_company_1.name)
        self.assertEqual(lead.contact_name, self.contact_1.name)
        # ensure partner did not void existing information
        self.assertEqual(lead.phone, '+1 202 555 9999')

        # invoke wizard and apply it
        convert = self.env['crm.lead.convert2ticket'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id
        }).create({
            'team_id': self.test_team.id,
            'ticket_type_id': self.test_ticket_type.id
        })
        convert.action_lead_to_helpdesk_ticket()

        # check created ticket coherency
        ticket = self.env['helpdesk.ticket'].sudo().search([('name', '=', lead.name)])
        self.assertTicketLeadConvertData(ticket, lead, self.test_team, self.test_ticket_type, self.contact_1)

    @users('user_sales_salesman')
    def test_lead_convert_to_ticket_w_partner_name(self):
        lead = self.lead_1.with_user(self.env.user)
        lead.write({
            'email_from': False,
            'partner_name': self.contact_1.name,
        })
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # invoke wizard and apply it
        convert = self.env['crm.lead.convert2ticket'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id
        }).create({
            'team_id': self.test_team.id,
            'ticket_type_id': self.test_ticket_type.id
        })
        convert.action_lead_to_helpdesk_ticket()

        # check created ticket coherency
        ticket = self.env['helpdesk.ticket'].sudo().search([('name', '=', lead.name)])
        self.assertTicketLeadConvertData(ticket, lead, self.test_team, self.test_ticket_type, self.contact_1)

    @users('user_sales_salesman')
    def test_lead_convert_to_ticket_w_contact_name(self):
        lead = self.lead_1.with_user(self.env.user)
        lead.write({
            'email_from': False,
            'contact_name': 'TURANGA',
        })
        self.assertEqual(lead.partner_id, self.env['res.partner'])

        # invoke wizard and apply it
        convert = self.env['crm.lead.convert2ticket'].with_context({
            'active_model': 'crm.lead',
            'active_id': self.lead_1.id
        }).create({
            'team_id': self.test_team.id,
            'ticket_type_id': self.test_ticket_type.id
        })
        convert.action_lead_to_helpdesk_ticket()

        # check created ticket coherency
        ticket = self.env['helpdesk.ticket'].sudo().search([('name', '=', lead.name)])
        self.assertTicketLeadConvertData(ticket, lead, self.test_team, self.test_ticket_type, self.contact_2)
