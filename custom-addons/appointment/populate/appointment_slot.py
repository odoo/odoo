# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

import pytz
from odoo import models
from odoo.addons.appointment.populate import data
from odoo.tools import populate


class AppointmentSlot(models.Model):
    _inherit = "appointment.slot"
    _populate_dependencies = [
        'res.company',
        'appointment.type',
    ]
    _populate_sizes = {'small': 120, 'medium': 320, 'large': 4000}

    def _populate_factories(self):
        def compute_hours_and_duration(iterator, *args):
            random = populate.Random('hoursduration')
            appointment_type_duration_max_half_day = max(
                data.appointment_type["appointment_duration_half_day"].keys())

            for values in iterator:
                app_type = self.env["appointment.type"].browse(values["appointment_type_id"])
                app_type_long_duration = app_type.appointment_duration > appointment_type_duration_max_half_day

                # 1/5 or always if appointment type duration > max duration for a half-day: give a
                # single slot starting from start of AM until end of PM (some of these slots will
                # be tagged 'allday')
                if random.random() < .2 or app_type_long_duration:
                    yield {
                        **values,
                        'start_hour': random.choices(
                            *zip(*data.appointment_slot.get("start_time_am").items()))[0],
                        'end_hour': random.choices(
                            *zip(*data.appointment_slot.get("end_time_pm").items()))[0],
                        'allday': random.random() < 0.5 if app_type_long_duration else False,
                    }
                else:  # Yield a morning and an afternoon slot
                    for start_hours, end_hours in zip(["start_time_am", "start_time_pm"],
                                                      ["end_time_am", "end_time_pm"]):
                        yield {
                            **values,
                            'start_hour': random.choices(
                                *zip(*data.appointment_slot.get(start_hours).items()))[0],
                            'end_hour': random.choices(
                                *zip(*data.appointment_slot.get(end_hours).items()))[0],
                            'allday': False,
                        }

        def _compute_slot_type_and_datetimes(iterator, *kwargs):
            # Yield one or two slots with specified start and end datetime attributes for
            # `category="custom"` appointment types with the required "unique" slot_type, or a
            # single "recurring" slot_type slot
            random = populate.Random('slottypes')
            for values in iterator:
                app_type = self.env["appointment.type"].browse(values["appointment_type_id"])

                if app_type.category != 'custom':
                    yield {**values, "slot_type": "recurring"}

                else:  # Create randomly placed unique slot(s)
                    start_datetime = (
                        datetime.datetime.now()
                        .replace(hour=8 + random.randint(0, 3),
                                 minute=5 * random.choice([0, 2, 3, 4, 6, 9, 10]),
                                 second=0)
                        + datetime.timedelta(days=int(values["weekday"]))
                        - datetime.datetime.now(pytz.timezone(app_type["appointment_tz"]))
                        .utcoffset())

                    new_values = {
                        "slot_type": "unique",
                        "start_datetime": start_datetime,
                        "end_datetime": start_datetime + datetime.timedelta(
                            hours=app_type["appointment_duration"]),
                        "allday": False
                    }
                    yield {**values, **new_values}
                    # Sometimes two per day, with a "taken" slot in-between
                    if random.random() < 0.5:
                        new_values["start_datetime"] += datetime.timedelta(
                            hours=2 * app_type["appointment_duration"])
                        new_values["end_datetime"] += datetime.timedelta(
                            hours=2 * app_type["appointment_duration"])
                        yield {**values, **new_values}

        appointment_type_ids = self.env['appointment.type'].browse(
            self.env.registry.populated_models['appointment.type']).filtered_domain([
                ('category', 'in', ['punctual', 'recurring', 'custom'])]).ids

        # We need values for 5-6 days for each appointment_type_id.
        # We populate 7 days then later randomly drop one or more
        slots = [
            populate.chain_factories([
                ('appointment_type_id', populate.iterate(appointment_type_ids)),
                ('weekday', populate.iterate([weekday])),
                ('_hours_duration', compute_hours_and_duration)
            ], self._name)
            for weekday in range(1, 8)
        ]

        def _compute_slot_times(iterator, *args):
            random = populate.Random('slottimes')
            for slot in slots:
                for new_values in slot:
                    if new_values["__complete"]:
                        break
                    new_values["weekday"] = str(
                        (new_values["weekday"] + new_values["appointment_type_id"]) % 8)
                    # Min 1 day without
                    if new_values["weekday"] == '0' or random.random() < 0.15:
                        continue
                    this_data = {**new_values, **next(iterator)}
                    yield this_data

        return [
            ('_this_data', _compute_slot_times),
            ('_slot_type_and_datetimes', _compute_slot_type_and_datetimes),
        ]
