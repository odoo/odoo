# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment_crm.tests.test_appointment_crm import AppointmentCRMTest
from odoo.addons.website.tests.test_website_visitor import MockVisitor


class WebsiteAppointmentCRMTest(AppointmentCRMTest, MockVisitor):
    @classmethod
    def setUpClass(cls):
        super(WebsiteAppointmentCRMTest, cls).setUpClass()
        # Following website_visitor partner_id compute method, for logged user, access_token = partner.id
        cls.visitor_contact_1 = cls.env['website.visitor'].create({
            "name": 'Visitor identified',
            "partner_id": cls.contact_1.id,
            "access_token": cls.contact_1.id,
        })
        cls.visitor_user_sales_leads = cls.env['website.visitor'].create({
            "name": 'Visitor identified',
            "partner_id": cls.user_sales_leads.partner_id.id,
            "access_token": cls.user_sales_leads.partner_id.id
        })
        cls.visitor_non_identified = cls.env['website.visitor'].create({
            "name": 'Visitor non identified',
            "access_token": 'c8d20bd006c3bf46b875451defb5991d'
        })

    def test_appointment_visitor_event_organizer(self):
        """ Test that when the event is created by the organizer, the visitor is not associated with the lead generated.
        """
        with self.mock_visitor_from_request(force_visitor=self.visitor_user_sales_leads):
            meeting = self._create_meetings_from_appointment_type(
                self.appointment_type_create, self.user_sales_leads, self.contact_1
            )
            self.assertFalse(meeting.opportunity_id.visitor_ids)

    def test_appointment_visitor_identified(self):
        """ Test that an identified visitor different of the event organizer that create an event generates a lead
        associated with that visitor. """
        with self.mock_visitor_from_request(force_visitor=self.visitor_contact_1):
            meeting = self._create_meetings_from_appointment_type(
                self.appointment_type_create, self.user_sales_leads, self.contact_1
            )
            self.assertEqual(meeting.opportunity_id.visitor_ids, self.visitor_contact_1)

    def test_appointment_visitor_non_identified(self):
        """ Test that a non identified visitor that create an event generates a lead associated with that visitor. """
        with self.mock_visitor_from_request(force_visitor=self.visitor_non_identified):
            meeting = self._create_meetings_from_appointment_type(
                self.appointment_type_create, self.user_sales_leads, self.contact_1
            )
            self.assertEqual(meeting.opportunity_id.visitor_ids, self.visitor_non_identified)
