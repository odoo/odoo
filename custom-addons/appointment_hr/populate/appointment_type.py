# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    def _populate(self, size):
        appointment_types = super()._populate(size)
        rand = populate.Random('appointment_type+anytime')

        # Create anytime appointment types for 30% of active employees
        staff_user_ids = self.env['res.users'].browse(
            self.env.registry.populated_models['res.users']).filtered_domain([('active', '=', True)])

        appointment_types_anytime = []
        for user_id in staff_user_ids:
            if user_id.with_company(user_id.company_id).employee_id and rand.random() > 0.7:
                appointment_types_anytime.append({
                    'staff_user_ids': user_id,
                    'appointment_tz': user_id.tz,
                    'category': 'anytime',
                    'work_hours_activated': True,
                    'max_schedule_days': 30,
                    'name': f'Meeting with {user_id.name}',
                })
        appointment_types |= self.create(appointment_types_anytime)

        return appointment_types
