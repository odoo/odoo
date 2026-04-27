# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta
from werkzeug.urls import url_encode

from odoo import http
from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.tests import common, tagged, users


@tagged('appointment_ui', 'post_install', '-at_install')
class AppointmentCrmUITest(AppointmentCommon, common.HttpCase):

    def test_apt_with_lead_anonymous_create_with_multi_company(self):
        """ Test that an anonymous user can create an appointment from the website using information
        from an existing contact that belongs to a different company than the one associated with the
        appointment user, with lead_create enabled. """
        apt = self.apt_type_bxls_2days
        apt.write({
            'lead_create': True,
            'is_published': True,
        })
        apt_user = self.staff_user_bxls
        self.assertFalse(apt.meeting_ids)

        partner = self.partner_employee_c2
        partner.company_id = self.company_2
        date_str = '2022-02-14 12:00:00'
        self.assertNotIn(self.company_2, apt_user.company_ids)
        initial_partner_count = self.env['res.partner'].search_count([('email', '=', partner.email)])

        apt_submit_url = f"/appointment/{apt.id}/submit?" + url_encode({
            'staff_user_id': apt_user.id,
            'date_time': date_str,
            'duration': 1,
        })

        self.authenticate(None, None)
        data = {
            "csrf_token": http.Request.csrf_token(self),
            "datetime_str": date_str,
            "duration_str": "1.0",
            "name": "12345",
            "email": partner.email,
            "phone": "12345"
        }
        response = self.url_open(apt_submit_url, data=data)
        self.assertEqual(response.status_code, 200)

        new_partner_count = self.env['res.partner'].search_count([('email', '=', partner.email)])
        self.assertEqual(new_partner_count, initial_partner_count + 1, "Expected one additional partner with the same email.")

        self.assertEqual(len(apt.meeting_ids), 1)
        lead = apt.meeting_ids.opportunity_id
        self.assertTrue(lead, "A lead should have been created with the meeting")
        self.assertTrue(lead.partner_id != partner and lead.partner_id.email == partner.email)
        attendee_partners = apt.meeting_ids.attendee_ids.mapped("partner_id")
        self.assertTrue(len(attendee_partners) == 2 and lead.partner_id in attendee_partners)

    @users('apt_manager')
    def test_route_create_custom_with_context(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        now = datetime.now()
        unique_slots = [{
            'start': (now + timedelta(hours=1)).replace(microsecond=0).isoformat(' '),
            'end': (now + timedelta(hours=2)).replace(microsecond=0).isoformat(' '),
            'allday': False,
        }, {
            'start': (now + timedelta(days=2)).replace(microsecond=0).isoformat(' '),
            'end': (now + timedelta(days=3)).replace(microsecond=0).isoformat(' '),
            'allday': True,
        }]
        lead = self.env['crm.lead'].sudo().create({'name': 'Test Lead'})
        request = self.url_open(
            "/appointment/appointment_type/create_custom",
            data=json.dumps({
                'params': {
                    'slots': unique_slots,
                    'context': {
                        'default_assign_method': 'time_resource',
                        'default_opportunity_id': lead.id,
                    },
                }
            }),
            headers={"Content-Type": "application/json"},
        ).json()
        result = request.get('result', dict())
        self.assertTrue(result.get('appointment_type_id'), 'The request returns the id of the custom appointment type')

        appointment_type = self.env['appointment.type'].browse(result['appointment_type_id'])
        # The default_assign_method should be ignored as the field is not whitelisted
        self.assertEqual(appointment_type.assign_method, 'resource_time')
        # The default_opportunity_id should be propagated as the field is whitelisted
        appointment_invite = self.env['appointment.invite'].search([('appointment_type_ids', 'in', appointment_type.ids)])
        self.assertEqual(appointment_invite.opportunity_id, lead)
