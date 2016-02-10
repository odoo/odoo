# -*- coding: utf-8 -*-

from .common import TestCrmCases


class TestLead2opportunity2win(TestCrmCases):

    def test_lead2opportunity2win(self):
        """ Tests for Test Lead 2 opportunity 2 win """

        CrmLead2OpportunityPartnerMass = self.env['crm.lead2opportunity.partner.mass']
        CalendarAttendee = self.env['calendar.attendee']

        crm_case_2 = self.env.ref('crm.crm_case_2')
        crm_case_3 = self.env.ref('crm.crm_case_3')
        crm_case_13 = self.env.ref('crm.crm_case_13')

        # In order to test the conversion of a lead into a opportunity,
        # I set lead to open stage.
        crm_case_3.write({'stage_id': self.stage_lead1_id})

        # I check if the lead stage is "Open".
        self.assertEqual(crm_case_3.stage_id.sequence, 1, 'Lead stage is Open')

        # Giving access rights of salesman to convert the lead into opportunity.
        # I convert lead into opportunity for exiting customer.
        crm_case_3.sudo(self.crm_salesman_id).convert_opportunity(self.partner2_id)

        # I check details of converted opportunity.
        self.assertEqual(crm_case_3.type, 'opportunity', 'Lead is not converted to opportunity!')
        self.assertEqual(crm_case_3.partner_id.id, self.partner2_id, 'Partner mismatch!')
        self.assertEqual(crm_case_3.stage_id.id, self.stage_lead1_id, 'Stage of opportunity is incorrect!')

        # Now I schedule meeting with customer.
        crm_case_3.action_schedule_meeting()

        # After communicated  with customer, I put some notes with contract details.
        crm_case_3.message_post(subject='Test note', body='Détails envoyés par le client sur ​​le FAX pour la qualité')

        # I convert mass lead into opportunity customer.
        mass = CrmLead2OpportunityPartnerMass.with_context({'active_model': 'crm.lead', 'active_ids': [crm_case_13.id, crm_case_2.id], 'active_id': crm_case_13.id}).create({
            'user_ids': [(6, 0, self.env.ref('base.user_root').ids)],
            'team_id': self.sales_team_dept_id
        })
        mass.sudo(self.crm_salesman_id).mass_convert()

        # Now I check first lead converted on opportunity.
        self.assertEqual(crm_case_13.name, "Plan to buy 60 keyboards and mouses", "Opportunity name not correct")
        self.assertEqual(crm_case_13.type, 'opportunity', "Lead is not converted to opportunity!")
        expected_partner = "Will McEncroe"
        self.assertEqual(crm_case_13.partner_id.name, expected_partner, "Partner mismatch! %s vs %s" % (crm_case_13.partner_id.name, expected_partner))
        self.assertEqual(crm_case_13.stage_id.id, self.stage_lead1_id, "Stage of probability is incorrect!")

        # Then check for second lead converted on opportunity.
        self.assertEqual(crm_case_2.name, "Interest in Your New Software", "Opportunity name not correct")
        self.assertEqual(crm_case_2.type, "opportunity", "Lead is not converted to opportunity!")
        self.assertEqual(crm_case_2.stage_id.id, self.stage_lead1_id, "Stage of probability is incorrect!")

        # I loose the second opportunity
        crm_case_2.case_mark_lost()

        # I check details of the opportunity after the loose
        self.assertEqual(crm_case_2.probability, 0.0, "Revenue probability should be 0.0!")

        # I confirm review needs meeting.
        self.env.ref('calendar.calendar_event_4').with_context({'active_model': 'calendar.event'}).write({'state': 'open'})

        # I invite a user for meeting.
        CalendarAttendee.create({'partner_id': self.ref('base.partner_root'), 'email': 'user@meeting.com'}).do_accept()
