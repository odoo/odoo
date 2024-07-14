# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.appointment.populate import data
from odoo.tools import populate


class AppointmentType(models.Model):
    _inherit = "appointment.type"
    _populate_dependencies = [
        'res.company',
        'res.partner',
        'calendar.alarm',
    ]
    _populate_sizes = {'small': 15, 'medium': 40, 'large': 500}

    def _populate_factories(self):
        reminder_ids = self.env.registry.populated_models['calendar.alarm']
        country_ids = self.env["res.country"].search([]).ids

        company_ids = self.env['res.company'].browse(self.env.registry.populated_models['res.company'])
        admin_ids = self.env.ref('base.user_admin')
        company_users = {company_id: (company_id.user_ids - admin_ids).ids
                         for company_id in company_ids if len(company_id.user_ids - admin_ids) > 0}

        def get_k_staff_users(random=None, **kwargs):
            staff_users = company_users[random.choice(list(company_users.keys()))]
            return random.sample(staff_users, random.randint(1, len(staff_users)))

        def get_tz(values, random=None, **kwargs):
            """Sets a timezone that matches at least one of the users'"""
            return random.choice(self.env["res.users"].browse(values['staff_user_ids'])).tz

        def get_up_to_two_reminders(random=None, **kwargs):
            reminders = self.env['calendar.alarm'].browse(random.sample(reminder_ids, 2))
            # Avoid sending two reminders at same time with same method
            if (len(reminders.mapped("alarm_type")) == 1
                    and len(reminders.mapped("duration_minutes")) == 1):
                return reminders[1:]
            return reminders

        def get_n_countries_or_false(random=None, **kwargs):
            n_countries = random.choices((0, 1, 4, 5, 8), (0.80, .05, .05, .05, 0.05))[0]
            if n_countries:
                return random.sample(country_ids, n_countries)
            return False

        return [
            ('name', populate.randomize(data.appointment_type['name'])),
            ('staff_user_ids', populate.compute(get_k_staff_users)),
            ('appointment_tz', populate.compute(get_tz)),
            ('country_ids', populate.compute(get_n_countries_or_false)),
            # weighted fields
            *((field_name, populate.iterate(*zip(*data.appointment_type[field_name].items())))
              for field_name in ["min_schedule_hours", "max_schedule_days",
                                 "min_cancellation_hours", "active", "assign_method"]),
            # Some will be changed for longer durations using another frequency dictionary
            ('appointment_duration', populate.iterate(
                *zip(*data.appointment_type["appointment_duration_half_day"].items()))),
            ('reminder_ids', populate.compute(get_up_to_two_reminders)),
            ('message_confirmation', populate.constant(
                "Congratulations, your appointment is booked. <br>"
                "You'll receive a conference call meeting link before the meeting.")),
        ]

    def _populate(self, size):
        appointment_types = super()._populate(size)
        random = populate.Random('zizizaseed')
        # Ensures at least one of each is created (for small population size)
        none_done_category = True
        none_done_duration = True
        for record in appointment_types:
            # Randomly create "custom"-category appointment types
            # Making custom category requires a single user from a company
            if none_done_category or random.random() < .1 and record.staff_user_ids:
                single_staff_user = record.staff_user_ids[0]
                (record.with_company(single_staff_user.company_id).with_user(single_staff_user.id)
                    .write({
                        "staff_user_ids": single_staff_user,
                        "appointment_tz": single_staff_user.tz,
                        "category": "custom"
                    }))
                none_done_category = False

            # Make some of them longer to be used with all day slots
            if none_done_duration or random.random() < .1:
                record.appointment_duration = random.choices(
                    *zip(*data.appointment_type["appointment_duration_all_day"].items()))[0]
                none_done_duration = False
        return appointment_types
