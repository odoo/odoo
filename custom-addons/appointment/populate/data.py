# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

appointment_type = {
    "active": {True: 0.99, False: 0.01},
    "appointment_duration_half_day": {
        1.: .7,
        0.5: .15,
        2.: .05,
        2.75: .05,
    },
    "appointment_duration_all_day": {
        6: .75,
        7: .15,
        8: .1
    },
    "assign_method": {"time_auto_assign": 0.8, "resource_time": 0.2},
    "max_schedule_days": {
        15: .7,
        30: .15,
        5: .08,
        2: .07
    },
    "min_cancellation_hours": {
        1.: .75,
        2.: .15,
        48.: .1
    },
    "min_schedule_hours": {
        1.: .75,
        2.5: .15,
        5.: .1
    },
    "name": ["Schedule a Demo {counter}", "Doctor Appointment {counter}", "Lawn mowing {counter}",
             "Hair cut {counter}", "Chimney sweep {counter}", "Plan a party {counter}",
             "Poker night {counter}", "Grape trampling {counter}"],
}
appointment_slot = {
    "end_time_am": {
        12.5: 0.8,
        13.: 0.15,
        11.5: 0.05
    },
    "end_time_pm": {
        17.: 0.65,
        16.5: 0.15,
        19.: 0.2,
    },
    "start_time_am": {
        8.: 0.85,
        8.5: 0.1,
        6: 0.05,
    },
    "start_time_pm": {
        13: 0.8,
        13.75: 0.1,
        12.5: 0.1,
    }
}
