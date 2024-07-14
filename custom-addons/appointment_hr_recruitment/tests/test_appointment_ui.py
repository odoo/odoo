# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.tests import common, tagged, users


@tagged('appointment_ui', 'post_install', '-at_install')
class AppointmentCrmUITest(AppointmentCommon, common.HttpCase):

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
        dep_rd = self.env['hr.department'].sudo().create({
            'name': 'Research & Development',
        })
        job_developer = self.env['hr.job'].sudo().create({
            'name': 'Test Job',
            'department_id': dep_rd.id,
            'no_of_recruitment': 5,
        })
        applicant = self.env['hr.applicant'].sudo().create({
            'name': 'Test Applicant',
            'partner_name': 'Test Applicant',
            'job_id': job_developer.id,
        })
        request = self.url_open(
            "/appointment/appointment_type/create_custom",
            data=json.dumps({
                'params': {
                    'slots': unique_slots,
                    'context': {
                        'default_assign_method': 'time_resource',
                        'default_applicant_id': applicant.id,
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
        self.assertEqual(appointment_invite.applicant_id, applicant)
