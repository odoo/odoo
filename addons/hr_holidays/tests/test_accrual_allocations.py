import datetime
import inspect
from datetime import date

from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo import Command
from odoo.tests import tagged, Form
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger
from odoo.tools.date_utils import parse_iso_date

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class AccrualPlanDuplicataError(Exception):
    """ Happens when there are 2 "identical" accrual plans """


class ArgumentsError(Exception):
    """ Happens when the arguments of the function are invalid """


@tagged('post_install', '-at_install', 'accruals')
class TestAccrualAllocations(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
        })

        accrual_plan_by_signature = {}
        work_entry_type_by_signature = {}

        def _create_accrual_plan(accrual_plan_by_signature, vals_list):
            """ Creates an accrual plan
                This function has 2 additionnal purposes:
                    - Avoid accrual plan duplicata
                    - Making you wonder whether the test you're adding hasn't already been created
                        Indeed, the tests below are mostly defined by the accrual plan(s) they are using, so if an accrual plan
                        already exists, it may mean that your test can be merge in an existing test / that an existing test should be improved
                        (to avoid creating more allocation and makin more database request)
            """
            vals_list['name'] = f'Accrual plan line {inspect.getouterframes(inspect.currentframe())[1].frame.f_lineno}'
            accrual_plan = cls.env['hr.leave.accrual.plan'].create(vals_list)
            plan_signature = _get_accrual_plan_signature(accrual_plan)
            if plan_signature in accrual_plan_by_signature:
                raise AccrualPlanDuplicataError(
                    f'Accrual plan duplicata detected with accrual plan named:\n{accrual_plan_by_signature[plan_signature]}\nSignature:\n{plan_signature}\nPlease take a look at the description of the "_create_accrual_plan" function')
            accrual_plan_by_signature[plan_signature] = accrual_plan.name
            return accrual_plan

        def _create_work_entry_type(work_entry_type_by_signature, vals_list):
            vals_list['name'] = vals_list['code'] = f'Work entry type line {inspect.getouterframes(inspect.currentframe())[1].frame.f_lineno}'
            work_entry_type = cls.env['hr.work.entry.type'].create(vals_list)
            work_entry_type_signature = _get_work_entry_type_signature(work_entry_type)
            if work_entry_type_signature in work_entry_type_by_signature:
                raise AccrualPlanDuplicataError(
                    f'Work entry type duplicata detected with work entry type named:\n{work_entry_type_by_signature[work_entry_type_signature]}\nSignature:\n{work_entry_type_signature}')
            work_entry_type_by_signature[work_entry_type_signature] = work_entry_type.name
            return work_entry_type

        def _get_accrual_plan_signature(accrual_plan):
            """ Returns the signature of the plan

                This function only takes what are considered the "most important" parameters into account, because considering the number
                of option an accrual plan has, it would be too heavy to create one unit test per combination of parameters.

                If you still wish to create a new test case for an accrual plan that has the same hash, simply modify the fields at the beginning
                of the new test.
            """
            plan_signature = (f"{accrual_plan.transition_mode},{accrual_plan.is_based_on_worked_time},{accrual_plan.accrued_gain_time}"
                f",{'carryover' if accrual_plan.can_be_carryover else 'no_carryover'},{accrual_plan.carryover_date}")
            for level in accrual_plan.level_ids:
                plan_signature += (f",{level.start_count},{level.start_type},{level.frequency},{level.added_value_type},"
                    f"{level.action_with_unused_accruals},{level.carryover_options},{'expiring' if level.accrual_validity else 'not_expiring'},{'capped' if level.cap_accrued_time else 'uncapped'},{'capped_y' if level.cap_accrued_time_yearly else 'uncapped_y'},")
            return plan_signature[:-1]

        def _get_work_entry_type_signature(work_entry_type):
            return (f"{work_entry_type.count_as},{work_entry_type.requires_allocation},{work_entry_type.elligible_for_accrual_rate},{work_entry_type.request_unit},"
                f"{work_entry_type.unit_of_measure},{work_entry_type.allocation_validation_type},{work_entry_type.allows_negative}")

        cls.work_entry_type = _create_work_entry_type(work_entry_type_by_signature, {
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.work_entry_type_hour = _create_work_entry_type(work_entry_type_by_signature, {
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
        })
        cls.work_entry_type_hour_day = _create_work_entry_type(work_entry_type_by_signature, {
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'hour',
        })
        cls.work_entry_type_day_hour = _create_work_entry_type(work_entry_type_by_signature, {
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'hr',
            'request_unit': 'hour',
            'unit_of_measure': 'day',
        })

        accrual_plan1_levels_fields = {
            'added_value_type': 'day',
            'frequency': 'monthly',
            'accrual_validity': True,
            'accrual_validity_count': 3,
            'accrual_validity_type': 'month',
            'action_with_unused_accruals': 'all',
        }
        accrual_plan1_levels = [
            Command.create({
                **accrual_plan1_levels_fields,
                'milestone_date': 'creation',
                'added_value': 1,
            }),
            Command.create({
                **accrual_plan1_levels_fields,
                'milestone_date': 'after',
                'start_count': 13,
                'start_type': 'month',
                'added_value': 2,
            }),
        ]
        cls.accrual_plan_start1 = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'start',
            'carryover_date': 'allocation',
            'can_be_carryover': True,
            'level_ids': accrual_plan1_levels,
        })
        cls.accrual_plan_end1 = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'carryover_date': 'allocation',
            'can_be_carryover': True,
            'level_ids': accrual_plan1_levels,
        })
        cls.work_entry_type_day = _create_work_entry_type(work_entry_type_by_signature, {
            'count_as': 'absence',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.accrual_plan_monthly_end = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'carryover_date': 'allocation',
            'can_be_carryover': True,
            'level_ids': [Command.create({
                'start_count': 0,
                'added_value_type': 'day',
                'added_value': 2,
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
            })],
        })

        accrual_plan2_levels_fields = {
            'added_value_type': 'day',
            'frequency': 'monthly',
            'accrual_validity': True,
            'accrual_validity_count': 3,
            'accrual_validity_type': 'month',
            'action_with_unused_accruals': 'all',
        }
        cls.accrual_plan2 = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'carryover_date': 'allocation',
            'can_be_carryover': True,
            'transition_mode': 'end_of_accrual',
            'level_ids': [
                Command.create({
                    **accrual_plan2_levels_fields,
                    'milestone_date': 'creation',
                    'added_value': 1,
                }),
                Command.create({
                    **accrual_plan2_levels_fields,
                    'milestone_date': 'after',
                    'start_count': 1,
                    'start_type': 'month',
                    'added_value': 2,
                }),
            ],
        })
        cls.accrual_plan_monthly_end_max_leaves = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Accrual Plan For Test',
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'carryover_date': 'allocation',
            'can_be_carryover': True,
            'level_ids': [Command.create({
                'start_count': 0,
                'added_value_type': 'day',
                'added_value': 2,
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
                'cap_accrued_time': True,
                'maximum_leave': 10,
            })],
        })
        cls.accrual_plan_yearly_max_carriedover_days_start = _create_accrual_plan(accrual_plan_by_signature, {
            'name': '21 days per year, 5 carryover max',
            'transition_mode': 'immediately',
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [
                Command.create({
                    'milestone_date': 'creation',
                    'added_value': 21,
                    'frequency': 'yearly',
                    "action_with_unused_accruals": "all",
                    "carryover_options": "limited",
                    "max_carriedover_duration": 5,
                }),
            ],
        })
        cls.accrual_plan_monthly_start_carryover_lost = _create_accrual_plan(accrual_plan_by_signature, {
            'name': '1 day per month start - carryover 1st of Mai',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '5',
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [
                Command.create({
                    'milestone_date': 'creation',
                    "added_value": 1,
                    "frequency": "monthly",
                    "action_with_unused_accruals": "lost",
                }),
            ],
        })
        first_accrual_plan_level = Command.create({
            'milestone_date': 'creation',
            'added_value_type': 'day',
            'added_value': 2,
            'frequency': 'monthly',
            'first_day': 15,
            'action_with_unused_accruals': 'all',
        })
        second_accrual_plan_level = Command.create({
            'milestone_date': 'after',
            'start_count': 12,
            'start_type': 'month',
            'added_value_type': 'day',
            'added_value': 3,
            'frequency': 'monthly',
            'first_day': 15,
            'action_with_unused_accruals': 'all',
        })
        cls.accrual_plan_monthly_start_carryover_year_start = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'level_ids': [first_accrual_plan_level],
        })
        cls.accrual_plan_monthly_end_carryover_year_start = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'level_ids': [first_accrual_plan_level],
        })

        cls.accrual_plan_monthly_end_carryover_year_start_2_lvls = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'transition_mode': 'immediately',
            'level_ids': [first_accrual_plan_level, second_accrual_plan_level],
        })

        cls.accrual_plan_monthly_start_carryover_year_start_2_lvls = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'transition_mode': 'immediately',
            'level_ids': [first_accrual_plan_level, second_accrual_plan_level],
        })

        cls.accrual_plan_monthly_start_carryover_lost_hour = _create_accrual_plan(accrual_plan_by_signature, {
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '5',
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [
                Command.create({
                    'milestone_date': 'creation',
                    "added_value": 8,
                    'added_value_type': 'hour',
                    "frequency": "monthly",
                    "action_with_unused_accruals": "lost",
                }),
            ],
        })

        cls.based_on_work_time_accrual_plan_daily = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': True,
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
            })],
        })

        cls.accrual_plan_daily_end_max_1_leave = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 1,
                'action_with_unused_accruals': 'all',
            })],
        })

        cls.accrual_plan_daily_1_hour_4_max_leave = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'hour',
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 4,
                'action_with_unused_accruals': 'all',
            })],
        })

        cls.weekly_accrual_plan = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'allocation',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 1,
                'frequency': 'daily',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
            })],
        })

        cls.accrual_plan_monthly_end_carry_over_lost_year_start = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day': '31',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
            })],
        })

        cls.work_entry_type_no_negative = cls.env['hr.work.entry.type'].create({
            'name': 'Test Accrual - No negative',
            'code': 'Test Accrual - No negative',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'allows_negative': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.work_entry_type_negative = cls.env['hr.work.entry.type'].create({
            'name': 'Test Accrual - Negative',
            'code': 'Test Accrual - Negative',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'allows_negative': True,
            'max_allowed_negative': 1,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.accrual_plan_period_end_montlhy_max_carryover_year_start = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day': '31',
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 5,
            })],
        })
        cls.dummy_accrual_plan = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
        })
        cls.accrual_plan_hourly_based_on_work = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': True,
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'hourly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_daily_end = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'carryover_date': 'allocation',
            'level_ids': [Command.create({
                'milestone_date': 'creation',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
                'action_with_unused_accruals': 'all',
                'cap_accrued_time': False,
            })],
        })
        cls.accrual_plan_daily_end_after_1d = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'carryover_date': 'allocation',
            'level_ids': [Command.create({
                'milestone_date': 'after',
                'start_count': 1,
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
                'action_with_unused_accruals': 'all',
                'cap_accrued_time': False,
            })],
        })
        cls.accrual_plan_weekly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'added_value_type': 'day',
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'weekly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_bimonthly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'bimonthly',
                'first_day': 1,
                'second_day': 15,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_monthly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'added_value_type': 'day',
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_biyearly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'biyearly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_yearly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_hourly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'hourly',
                'action_with_unused_accruals': 'all',
                'cap_accrued_time': True,
                'maximum_leave': 10000,
            })],
        })
        cls.accrual_plan_based_on_worked_time = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': True,
            'can_be_carryover': True,
            'level_ids': [Command.create({
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 5,
                'frequency': 'weekly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_monthly_31th_max_carryover_duration = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'hour',
                'first_day': 31,
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 4,
            })],
        })
        cls.accrual_plan_2_lvls_weekly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'weekly',
                'cap_accrued_time': True,
                'maximum_leave': 1,
            }), (0, 0, {
                'milestone_date': 'after',
                'start_count': 10,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'weekly',
                'cap_accrued_time': True,
                'maximum_leave': 1,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_daily_carryover_lost = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 20,
                'action_with_unused_accruals': 'lost',
            })],
        })
        cls.accrual_plan_yearly_carryover_limited_10 = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 2,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 10,
            })],
        })
        cls.accrual_plan_daily_max_leave_carryover_limited = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 25,
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 15,
            })],
        })
        cls.accrual_plan_biyearly_2_levels = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Accrual Plan For Test',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 15,
                'frequency': 'biyearly',
                'action_with_unused_accruals': 'all',
            }), (0, 0, {
                'milestone_date': 'after',
                'start_count': 4,
                'start_type': 'month',
                'added_value': 10,
                'frequency': 'biyearly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_3_levels_monthly_max_leaves = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Accrual Plan For Test',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 2,
                'start_type': 'month',
                'added_value': 3,
                'frequency': 'monthly',
                'cap_accrued_time': True,
                'maximum_leave': 3,
                'action_with_unused_accruals': 'all',
                'first_day': 31,
            }), (0, 0, {
                'milestone_date': 'after',
                'start_count': 3,
                'start_type': 'month',
                'added_value': 6,
                'frequency': 'monthly',
                'cap_accrued_time': True,
                'maximum_leave': 6,
                'action_with_unused_accruals': 'all',
                'first_day': 31,
            }), (0, 0, {
                'milestone_date': 'after',
                'start_count': 4,
                'start_type': 'month',
                'added_value': 1,
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
                'first_day': 31,
            })],
        })
        cls.accrual_plan_yearly_carryover_lost = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [
                (0, 0, {
                    'milestone_date': 'creation',
                    'added_value': 3,
                    'added_value_type': 'day',
                    'frequency': 'yearly',
                    'action_with_unused_accruals': 'lost',
                }),
            ],
        })
        cls.accrual_plan_weekly_5_max_leave = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Accrual Plan For Test',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'weekly',
                'cap_accrued_time': True,
                'maximum_leave': 5,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_weekly_hour_max_leaves = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Accrual Plan For Test',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 3,
                'added_value_type': 'hour',
                'frequency': 'weekly',
                'cap_accrued_time': True,
                'maximum_leave': 10,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_daily_5_max_leaves = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 1,
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 5,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_hourly_max_leaves_capped_yearly = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 1,
                'added_value_type': 'hour',
                'frequency': 'hourly',
                'cap_accrued_time': True,
                'maximum_leave': 24,
                'cap_accrued_time_yearly': True,
                'maximum_leave_yearly': 16,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_monthly_start_15_max_leaves = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 1.5,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'first_day': 13,
                'cap_accrued_time': True,
                'maximum_leave': 4,
                'action_with_unused_accruals': 'all',
            })],
        })

        cls.accrual_plan_2_lvls_start_weekly_max_leaves = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [
                (0, 0, {
                    'added_value_type': 'day',
                    'milestone_date': 'creation',
                    'added_value': 1,
                    'frequency': 'weekly',
                    'week_day': '2',
                    'cap_accrued_time': True,
                    'maximum_leave': 8,
                }),
                (0, 0, {
                    'milestone_date': 'after',
                    'start_count': 3,
                    'start_type': 'month',
                    'added_value': 2,
                    'frequency': 'weekly',
                    'week_day': '2',
                    'cap_accrued_time': True,
                    'maximum_leave': 5,
                }),
            ],
        })
        cls.work_entry_type_absence_half_day_day = _create_work_entry_type(work_entry_type_by_signature, {
            'name': 'Paid Time Off 2',
            'code': 'Paid Time Off 2',
            'requires_allocation': False,
            'count_as': 'absence',
            'request_unit': 'half_day',
            'unit_of_measure': 'day',
        })
        cls.work_entry_type_accrual_non_elligible_absence_day_day = _create_work_entry_type(work_entry_type_by_signature, {
            'name': 'Paid Time Off 2',
            'code': 'Paid Time Off 2',
            'count_as': 'absence',
            'requires_allocation': False,
            'elligible_for_accrual_rate': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.work_entry_type_accrual_elligible_absence_day_day = _create_work_entry_type(work_entry_type_by_signature, {
            'name': 'Paid Time Off 2',
            'code': 'Paid Time Off 2',
            'count_as': 'absence',
            'requires_allocation': False,
            'elligible_for_accrual_rate': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.work_entry_type_working_time_day_day = _create_work_entry_type(work_entry_type_by_signature, {
            'name': 'Remote Work',
            'code': 'Remote Work',
            'count_as': 'working_time',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.accrual_plan_monthly_start_max_69_carriedover = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 20,
            'carryover_month': '4',
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 10,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'first_day': 11,
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 69,
            })],
        })
        cls.accrual_plan_3_lvls_monthly_biyearly_yearly_carryover_policy_change = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'end',
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 5,
            'carryover_month': '6',
            'level_ids': [
                (0, 0, {
                    'added_value_type': 'day',
                    'milestone_date': 'after',
                    'start_count': 5,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'monthly',
                    'first_day': 9,
                    'cap_accrued_time': True,
                    'maximum_leave': 15,
                    'action_with_unused_accruals': 'all',
                    'carryover_options': 'limited',
                    'max_carriedover_duration': 13,
                }),
                (0, 0, {
                    'milestone_date': 'after',
                    'start_count': 9,
                    'start_type': 'month',
                    'added_value': 2,
                    'frequency': 'biyearly',
                    'first_month_day': 17,
                    'first_month': '2',
                    'second_month_day': 29,
                    'second_month': '10',
                    'cap_accrued_time': True,
                    'maximum_leave': 10,
                    'action_with_unused_accruals': 'all',
                    'carryover_options': 'limited',
                    'max_carriedover_duration': 20,
                }),
                (0, 0, {
                    'milestone_date': 'after',
                    'start_count': 17,
                    'start_type': 'month',
                    'added_value': 12,
                    'frequency': 'yearly',
                    'yearly_month': '7',
                    'yearly_day': 15,
                    'cap_accrued_time': True,
                    'maximum_leave': 21,
                    'action_with_unused_accruals': 'lost',
                }),
            ],
        })
        cls.accrual_plan_weekly_carryover_lost = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'allocation',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 1,
                'frequency': 'weekly',
                'cap_accrued_time': False,
                'action_with_unused_accruals': 'lost',
            })],
        })
        cls.work_entry_type_absence_hour_hour = _create_work_entry_type(work_entry_type_by_signature, {
            'name': 'Test Leave Type 2',
            'code': 'Test Leave Type 2',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'no_validation',
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
        })
        cls.accrual_plan_monthly_hour = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'hour',
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_monthly_start_carryover_allocation_lost = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'carryover_date': 'allocation',
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'first_day': 27,
                'action_with_unused_accruals': 'lost',
            })],
        })
        cls.accrual_plan_monthly_carryover_all = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': False,
            'accrued_gain_time': 'end',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 4,
                'added_value_type': 'hour',
                'frequency': 'monthly',
                'cap_accrued_time': True,
                'maximum_leave': 100,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_daily_start_max_leaves_carryover_year_start = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'daily',
                'cap_accrued_time': True,
                'maximum_leave': 10,
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_daily_carryover_year_start_all_work_time = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': True,
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'accrued_gain_time': 'end',
            'level_ids': [
                (0, 0, {
                    'added_value_type': 'day',
                    'milestone_date': 'after',
                    'start_count': 1,
                    'start_type': 'day',
                    'added_value': 1,
                    'frequency': 'daily',
                    'action_with_unused_accruals': 'all',
                }),
            ],
        })
        cls.accrual_plan_2_lvls_yearly_carryover_lost = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '7',
            'level_ids': [(0, 0, {
                'added_value': 12,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'milestone_date': 'creation',
                'action_with_unused_accruals': 'lost',
            }),
            (0, 0, {
                'added_value': 14,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'milestone_date': 'after',
                'start_count': 18,
                'start_type': 'month',
                'action_with_unused_accruals': 'lost',
            })],
        })
        cls.accrual_plan_2_lvls_monthly_carryover_lost_limited = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '6',
            'level_ids': [(0, 0, {
                'added_value': 1,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'milestone_date': 'creation',
                'action_with_unused_accruals': 'lost',
            }),
            (0, 0, {
                'added_value': 2,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'milestone_date': 'after',
                'start_count': 9,
                'start_type': 'month',
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 5,
            })],
        })
        cls.accrual_plan_2_lvls_start_yearly_carryover_lost_all = _create_accrual_plan(accrual_plan_by_signature, {
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '6',
            'level_ids': [(0, 0, {
                'added_value': 10,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'milestone_date': 'creation',
                'action_with_unused_accruals': 'lost',
            }),
            (0, 0, {
                'added_value': 12,
                'added_value_type': 'day',
                'frequency': 'yearly',
                'milestone_date': 'after',
                'start_count': 32,
                'start_type': 'month',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_2_lvls_biyearly_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '4',
            'level_ids': [(0, 0, {
                'milestone_date': 'creation',
                'added_value': 10,
                'added_value_type': 'day',
                'frequency': 'biyearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 5,
            }),
            (0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 13,
                'start_type': 'month',
                'added_value': 15,
                'frequency': 'biyearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            })],
        })
        cls.accrual_plan_2_lvls_yearly_monthly_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '5',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            }),
            (0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'after',
                'start_count': 20,
                'start_type': 'month',
                'added_value': 20,
                'frequency': 'monthly',
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 3,
            })],
        })
        cls.accrual_plan_monthly_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '5',
            'accrued_gain_time': 'start',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 1,
                'frequency': 'monthly',
                'first_day': 15,
                'action_with_unused_accruals': 'all',
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 2,
            })],
        })
        cls.accrual_plan_yearly_start_max_carriedover_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'other',
            'accrued_gain_time': 'start',
            'carryover_day': 20,
            'carryover_month': '9',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 5,
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 4,
            })],
        })
        cls.accrual_plan_2_levels_biyearly_start_limited_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '4',
            'accrued_gain_time': 'start',
            'level_ids': [(0, 0, {
                    'added_value_type': 'day',
                    'milestone_date': 'creation',
                    'added_value': 10,
                    'frequency': 'biyearly',
                    'action_with_unused_accruals': 'all',
                    'accrual_validity': True,
                    'accrual_validity_type': 'month',
                    'accrual_validity_count': 7,
                    'carryover_options': 'limited',
                    'max_carriedover_duration': 5,
                }), (0, 0, {
                    'added_value_type': 'day',
                    'milestone_date': 'after',
                    'start_count': 8,
                    'start_type': 'month',
                    'added_value': 15,
                    'frequency': 'biyearly',
                    'action_with_unused_accruals': 'all',
                    'carryover_options': 'limited',
                    'max_carriedover_duration': 10,
                },
            )],
        })
        cls.accrual_plan_yearly_carryover_limited_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'can_be_carryover': True,
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '4',
            'level_ids': [(0, 0, {
                'added_value_type': 'day',
                'milestone_date': 'creation',
                'added_value': 10,
                'frequency': 'yearly',
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 5,
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 5,
            })],
        })
        cls.accrual_plan_yearly_start_max_leave_carryover_limited = _create_accrual_plan(accrual_plan_by_signature, {
            'transition_mode': 'immediately',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
            'level_ids': [(0, 0, {
                "milestone_date": 'creation',
                "added_value": 21,
                "cap_accrued_time": True,
                "maximum_leave": 28,
                "frequency": "yearly",
                "action_with_unused_accruals": "all",
                "carryover_options": "limited",
                "max_carriedover_duration": 7,
            })],
        })
        cls.accrual_plan_no_level_start_carryover_year_start = _create_accrual_plan(accrual_plan_by_signature, {
            'transition_mode': 'immediately',
            'can_be_carryover': True,
            'carryover_date': 'year_start',
            'accrued_gain_time': 'start',
        })
        cls.employee_without_calendar = cls.env['hr.employee'].create({
            'name': 'employee without calendar',
            'resource_calendar_id': False,
        })
        cls.accrual_plan_hourly_work_time = _create_accrual_plan(accrual_plan_by_signature, {
            'is_based_on_worked_time': True,
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'milestone_date': 'after',
                'start_count': 1,
                'start_type': 'day',
                'added_value': 1,
                'added_value_type': 'hour',
                'frequency': 'hourly',
                'action_with_unused_accruals': 'all',
            })],
        })
        cls.accrual_plan_daily_hour = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'end',
            'level_ids': [(0, 0, {
                'added_value_type': 'hour',
                'start_count': 0,
                'start_type': 'day',
                'added_value': 1,
                'frequency': 'daily',
            })],
        })
        cls.work_entry_type_absence_requires_alloc_half_day_day = _create_work_entry_type(work_entry_type_by_signature, {
            'name': 'Test Leave Type 2',
            'code': 'Test Leave Type 2',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'no_validation',
            'request_unit': 'half_day',
            'unit_of_measure': 'day',
        })
        level_vals = {
            'milestone_date': 'after',
            'accrual_validity': True,
            'accrual_validity_count': 6,
            'accrual_validity_type': 'month',
            'accrued_gain_time': 'start',
            'action_with_unused_accruals': 'all',
            'cap_accrued_time': True,
            'frequency': 'yearly',
            'carryover_options': 'limited',
            'max_carriedover_duration': 5,
        }
        cls.accrual_plan_4_lvls_start_max_leaves_carryover_limited_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Test accrual plan',
            'accrued_gain_time': 'start',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                    **level_vals,
                    'added_value': 20,
                    'milestone_date': 'creation',
                    'maximum_leave': 25,
                }), (0, 0, {
                    **level_vals,
                    'added_value': 21,
                    'start_count': 2,
                    'start_type': 'year',
                    'maximum_leave': 26,
                }), (0, 0, {
                    **level_vals,
                    'added_value': 22,
                    'start_count': 4,
                    'start_type': 'year',
                    'maximum_leave': 27,
                }), (0, 0, {
                    **level_vals,
                    'added_value': 23,
                    'start_count': 6,
                    'start_type': 'year',
                    'maximum_leave': 28,
                }),
            ],
        })
        cls.accrual_plan_monthly_start = _create_accrual_plan(accrual_plan_by_signature, {
            'name': '2 Days Every 1st of Month',
            'accrued_gain_time': 'start',
            'level_ids': [Command.create({
                'added_value': 2,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'first_day': 1,
                'action_with_unused_accruals': 'all',
                'milestone_date': 'creation',
            })],
        })
        cls.calendar_8h_per_day = cls.env['resource.calendar'].create({
            'name': 'Standard 40h Test Calendar',
            'hours_per_day': 8.0,
        })
        cls.accrual_plan_monthly_start_carryover_limited_expiring = _create_accrual_plan(accrual_plan_by_signature, {
            'name': 'Accrual Plan For Test',
            'accrued_gain_time': 'start',
            'carryover_date': 'other',
            'carryover_day': 1,
            'carryover_month': '11',
            'can_be_carryover': True,
            'level_ids': [(0, 0, {
                'added_value': 2,
                'added_value_type': 'day',
                'frequency': 'monthly',
                'milestone_date': 'creation',
                'action_with_unused_accruals': 'all',
                'carryover_options': 'limited',
                'max_carriedover_duration': 5,
                'accrual_validity': True,
                'accrual_validity_type': 'month',
                'accrual_validity_count': 1,
            })],
        })
        cls.work_entry_type_absence_requires_alloc_negativ = _create_work_entry_type(work_entry_type_by_signature, {
            'name': 'Test Accrual',
            'code': 'Test Accrual',
            'count_as': 'absence',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'allows_negative': True,
            'max_allowed_negative': 2,
            'unit_of_measure': 'day',
        })
        cls.dummy_test_employee = cls.env['hr.employee'].create([{
            'name': 'Department Employee 1',
            'company_id': cls.company.id,
        }])
        cls.accrual_plan_daily_hour_work_time = cls.env['hr.leave.accrual.plan'].create({
            'name': 'Daily Worked Time Accrual',
            'is_based_on_worked_time': True,
            'accrued_gain_time': 'end',
            'can_be_carryover': True,
            'carryover_date': 'allocation',
            'level_ids': [Command.create({
                'milestone_date': 'creation',
                'added_value': 5,
                'added_value_type': 'hour',
                'frequency': 'daily',
                'action_with_unused_accruals': 'all',
            })],
        })

    def _run_update_accrual_cron(self, target_date=None):
        self.env['hr.leave.allocation']._get_to_update_accrual_allocations()._update_accrual(target_date)

    def _get_period_days(self, start_date, end_date):
        """ Parameter `end_date` included """
        if not (len(start_date) == len(end_date) == 10):
            raise ArgumentsError('Expected a date (not a datetime) with the format YYYY-MM-DD!')
        return (parse_iso_date(end_date) - parse_iso_date(start_date)).days + 1

    def _assert_accrual_allocation_nbr_of_days_and_nextcall(self, allocation, assertions_by_date):
        """
        For each given tuple of the assertion, update the accrual at the given date,
        then assert the 'number_of_days' and the 'nextcall' of the allocation
        :param assertions: iterable of tuples with:
            - test date
            - ('number_of_days', 'nextcall') tuple
        """
        self._assert_accrual_allocation(allocation, assertions_by_date, ('number_of_days', 'nextcall'))

    def _build_create_leave_command(self, employee, work_entry_type):
        return (
            lambda date_from, date_to, approve=True:
                lambda: self._create_leave(employee, work_entry_type, date_from, date_to, validate=approve))

    def _assert_accrual_allocation(self, allocation, assertions, tested_fields):
        """ For each assertion, assert allocation `tested_fields` values after running accrual update for the given test date
            :param assertions: iterable of tuples with:
                - test date
                - iterable of the expected values matching `tested_fields`

            For each test date, run the accrual cron and assert field values.
            :param tested_fields: iterable of the name of the allocation fields to be tested
        """
        for target_date, *field_values in assertions:
            with freeze_time(target_date):
                self._run_update_accrual_cron()
                error_msg_suffix = f'Error on {target_date}'
                for field, expected_value in zip(tested_fields, field_values):
                    self.assertEqual(allocation[field], expected_value, f'{error_msg_suffix} - wrong value for field {field}')

    def _assert_get_allocation_data(self, allocation, allocation_values_by_date, tested_fields):
        """ Assert allocation and balance data from `get_allocation_data` for each test date.
            :param allocation_values_by_date: iterable of tuples with:
                - test date
                - iterable of the expected values matching `tested_fields`, or a callable

            If values are provided, run the accrual cron before asserting.
            If it's a callable, simply call it at the given date.
            "Durations" use the allocation request unit.
            The value for the field 'allocated_duration' should always be specified (give the work entry type allocated duration).
            If the value for the field 'remaining_leaves' is not specified, it will be considered equal to the 'allocated_duration' (usefull for test case with no leaves).
        """
        if 'allocated_duration' not in tested_fields:
            raise ArgumentsError('The field allocated_duration must be asserted!')

        work_entry_allocations = self.env['hr.leave.allocation'].with_context(active_test=False).search([
            ('employee_id', '=', allocation.employee_id.id),
            ('work_entry_type_id', '=', allocation.work_entry_type_id.id),
            ('accrual_plan_id', '!=', False),
            ('state', '=', 'validate'),
        ])
        self.assertEqual(work_entry_allocations, allocation, 'This test helper method only works if there is exactly one accrual allocation linked to the work entry type')

        work_entry_type = allocation.work_entry_type_id
        employee = allocation.employee_id
        for i, (target_date, *field_values) in enumerate(allocation_values_by_date):
            with freeze_time(target_date):
                if callable(field_values[0]):
                    field_values[0]()
                    continue

                self._run_update_accrual_cron()
                error_msg_suffix = f'On {target_date} - assertion {i}'
                expected_work_entry_type_remaining_leaves = None
                expected_work_entry_type_allocated_duration = None
                for field, expected_value in zip(tested_fields, field_values):
                    if field == 'allocated_duration':
                        expected_work_entry_type_allocated_duration = expected_value
                        continue
                    if field == 'remaining_leaves':
                        expected_work_entry_type_remaining_leaves = expected_value
                        continue
                    self.assertEqual(allocation[field], expected_value, f'{error_msg_suffix} - wrong value for field {field}')

                if expected_work_entry_type_allocated_duration is None:
                    raise ArgumentsError('Could not find the field "time_off_type_allocated_duration" in the assertion_structure.')

                if expected_work_entry_type_remaining_leaves is None:
                    expected_work_entry_type_remaining_leaves = expected_work_entry_type_allocated_duration

                work_entry_type_data = work_entry_type.get_allocation_data(employee, target_date)
                remaining_leaves = work_entry_type_data[employee][0][1]['remaining_leaves']
                leaves_taken = work_entry_type_data[employee][0][1]['leaves_taken']
                work_entry_duration = remaining_leaves + leaves_taken
                self.assertAlmostEqual(work_entry_duration, expected_work_entry_type_allocated_duration,
                    msg=f'{error_msg_suffix} - Incorrect allocated duration', delta=0.01)
                self.assertAlmostEqual(remaining_leaves, expected_work_entry_type_remaining_leaves,
                    msg=f'{error_msg_suffix} - Incorrect remaining leaves', delta=0.01)

    def _assert_get_allocation_data_future(self, allocation, assertions):
        """ Assert allocation and balance future data from get_allocation_data for each test date.
            :param allocation_values_by_date: iterable of tuples with:
                - test date
                - (allocated_duration, remaining leaves) tuple for the work entry type of the given allocation,
                using the unit `allocation.work_entry_type_id.unit_of_measure`
        """
        work_entry_type = allocation.work_entry_type_id
        employee = allocation.employee_id
        for i, (target_date, *assertion) in enumerate(assertions):
            if callable(assertion[0]):
                with freeze_time(target_date):
                    assertion[0]()
                    continue

            if len(assertion) == 2:
                expected_allocated_duration, expected_left_duration = assertion
            elif len(assertion) == 1:
                expected_allocated_duration = expected_left_duration = assertion[0]
            else:
                raise ArgumentsError(f'One assertion should be compose of 1 or 2 float values, got {assertion}')
            work_entry_type_data = work_entry_type.get_allocation_data(employee, target_date)
            remaining_leaves = work_entry_type_data[employee][0][1]['remaining_leaves']
            leaves_taken = work_entry_type_data[employee][0][1]['leaves_taken']
            work_entry_duration = remaining_leaves + leaves_taken
            error_msg_suffix = f'On {target_date} - Assertion {i}'
            self.assertAlmostEqual(remaining_leaves, expected_left_duration, msg=f'{error_msg_suffix} - Incorrect remaining leaves duration', delta=0.01)
            self.assertAlmostEqual(work_entry_duration, expected_allocated_duration, msg=f'{error_msg_suffix} - Incorrect allocated duration', delta=0.01)

    @freeze_time('2025-09-01')
    def test_frequency_daily_worked_time_non_utc_timezone(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Brisbane 40 Hours',
            'hours_per_day': 8,
            'attendance_ids': [
                Command.create({
                    'dayofweek': str(weekday),
                    'hour_from': 8,
                    'hour_to': 12,
                })
                for weekday in range(5)
            ] + [
                Command.create({
                    'dayofweek': str(weekday),
                    'hour_from': 13,
                    'hour_to': 17,
                })
                for weekday in range(5)
            ],
        })
        self.employee_emp.tz = 'Australia/Brisbane'
        self.employee_emp.resource_calendar_id = calendar
        self.user_hrmanager.tz = 'Australia/Brisbane'
        accrual_plan = self.accrual_plan_daily_hour_work_time
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager).create({
            'name': 'Brisbane Daily Accrual',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type_hour.id,
            'date_from': date(2025, 9, 1),
            'number_of_days': 0,
        })
        allocation.action_approve()

        self._assert_accrual_allocation(allocation, (
                ("2025-09-02", 5),
                ("2025-09-03", 10),
                ("2025-09-04", 15),
                ("2025-09-05", 20),
                ("2025-09-06", 25),
                ("2025-09-07", 25),
                ("2025-09-08", 25),
            ),
            ['number_of_hours_display'],
        )

    def test_consistency_between_cap_accrued_time_and_maximum_leave(self):
        accrual_plan = self.accrual_plan_hourly
        level = accrual_plan.level_ids
        level.maximum_leave = 10
        self.assertEqual(accrual_plan.level_ids.maximum_leave, 10)

        with self.assertRaises(UserError):
            level.maximum_leave = 0

        level.cap_accrued_time = False
        self.assertEqual(accrual_plan.level_ids.maximum_leave, 0)

    def test_accrual_unlink(self):
        """ Assert unlinking an accrual plan that is still linked to an allocation raises an error """
        accrual_plan = self.dummy_accrual_plan
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 0,
        })

        with self.assertRaises(ValidationError):
            accrual_plan.unlink()

        allocation.unlink()
        accrual_plan.unlink()

    def test_frequency_hourly(self):
        """ Assert number of days and nextcall are computed correctly for a one level hourly accrual plan based on work time """
        with freeze_time("2017-12-05"):
            accrual_plan = self.accrual_plan_hourly_based_on_work
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Assert running the cron doesn't change anything
            ('2017-12-05', 0, False),
            ('2017-12-07', 8, date(2017, 12, 8)),
            # Assert running the cron again doesn't change anything
            ('2017-12-07', 8, date(2017, 12, 8)),
        ))

    def test_frequency_hourly_with_leaves(self):
        """ Assert number of days and nextcall are computed correctly for a one level hourly accrual plan based on work time
            while taking leaves
        """
        with freeze_time("2017-12-05"):
            accrual_plan = self.accrual_plan_hourly_based_on_work
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()
            self.assertEqual(allocation.nextcall, False)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

            self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
                # Assert running the cron doesn't change anything
                ('2017-12-05', 0, False),
            ))

            work_entry_type = self.work_entry_type_absence_half_day_day
            leave = self.env['hr.leave'].create({
                'name': 'leave',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': work_entry_type.id,
                'request_date_from': '2017-12-06 08:00:00',
                'request_date_to': '2017-12-06 17:00:00',
                'request_date_from_period': 'am',
                'request_date_to_period': 'am',
            })
            leave.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Accrual for the day 2017-12-06:
            # One day elapsed since the beginning of the first level = 1d * 8 (8 hours of work / day) - 1d * 4 (half a day leave)
            ('2017-12-07', 4, date(2017, 12, 8)),
            # Assert running the cron again doesn't change anything
            ('2017-12-07', 4, date(2017, 12, 8)),
        ))

    def test_frequency_daily(self):
        """ Assert number of days and nextcall are computed correctly for a one level daily accrual plan """
        with freeze_time("2017-12-05"):
            accrual_plan = self.accrual_plan_daily_end_after_1d
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Assert running the cron doesn't change anything
            ('2017-12-05', 0, False),
            # One day elapsed since the beginning of the first level
            ('2017-12-07', 1, date(2017, 12, 8)),
            # Assert running the cron again doesn't change anything
            ('2017-12-07', 1, date(2017, 12, 8)),
        ))

    def test_frequency_weekly(self):
        """ Assert number of days and nextcall are computed correctly for a one level weekly accrual plan
            Also do not approve the accrual plan right away
        """
        with freeze_time("2017-12-05"):
            accrual_plan = self.accrual_plan_weekly
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'date_from': '2021-09-03',
            })
        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Assert running the cron doesn't change anything
            ('2017-12-05', 0, False),
        ))

        with freeze_time("2017-12-07"):
            allocation.action_approve()
        self.assertEqual(allocation.nextcall, False)
        self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Date from is in the future, nextcall should still be None
            ('2017-12-07', 0, False),
            # Assert running the cron again doesn't change anything
            ('2017-12-07', 0, False),
            # Only 2 days elapsed since the beginning of the first level: 2021-09-04 and 2021-09-05 (don't accrue for the current day)
            ('2021-09-06', duration := 2 / 7, date(2021, 9, 13)),
            # An entire week elapsed
            ('2021-09-13', duration + 1, date(2021, 9, 20)),
        ))

    def test_frequency_bimonthly(self):
        """ Assert number of days and nextcall are computed correctly for a one level accruing twice a month accrual plan """
        with freeze_time('2021-09-01'):
            accrual_plan = self.accrual_plan_bimonthly
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'date_from': '2021-09-03',
            })
            allocation.action_approve()
            self.assertEqual(allocation.nextcall, False)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # The start of the first plan is in the future, nextcall should be False, no accrued days
            ('2021-09-01', 0, False),
            # Assert running the cron again doesn't change anything
            ('2021-09-01', 0, False),
            # Second day of the accrual plan is 15
            # Prorated: 09-04 -> 09-15 (not included)
            ('2021-09-15', duration := (14 - 3) / 14, date(2021, 10, 1)),
            # One day before the next accrual
            ('2021-09-30', duration, date(2021, 10, 1)),
            # First day of the accrual plan is 1, so there should be an full accrual for 09-15 -> 10-01 (not included)
            ('2021-10-01', duration + 1, date(2021, 10, 15)),
        ))

    def test_frequency_monthly(self):
        """ Assert number of days and nextcall are computed correctly for a one level monthly accrual plan """
        with freeze_time('2021-09-01'):
            accrual_plan = self.accrual_plan_monthly
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'date_from': '2021-08-31',
            })
            allocation.action_approve()
            self.assertEqual(allocation.nextcall, False)
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # The start of the first level is past, nextcall should be set, no accrued days
            ('2021-09-01', 0, date(2021, 10, 1)),
            # Assert running the cron again doesn't change anything
            ('2021-09-01', 0, date(2021, 10, 1)),
            # One day before the first accrual, nothing changed
            ('2021-09-30', 0, date(2021, 10, 1)),
            # First accrual happens
            ('2021-10-01', 1, date(2021, 11, 1)),
            # One day before the second accrual
            ('2021-10-31', 1, date(2021, 11, 1)),
            # Second accrual
            ('2021-11-01', 2, date(2021, 12, 1)),
        ))

    def test_frequency_biyearly(self):
        """ Assert number of days and nextcall are computed correctly for a one level accruing twice a year accrual plan """
        with freeze_time('2021-09-01'):
            accrual_plan = self.accrual_plan_biyearly
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # The start of the first plan is in the future (tomorrow), nextcall should be False, no accrued days
            ('2021-09-01', 0, False),
            # Assert running the cron again doesn't change anything
            ('2021-09-01', 0, False),
            # One day before the first accrual, nothing changed
            ('2021-12-31', 0, date(2022, 1, 1)),
            # 2021-09-02 -> 2022-01-01: 4 month out of the 6 month of the first period
            ('2022-01-01', days := (29 + 31 + 30 + 31) / 184, date(2022, 7, 1)),
            # One day before the second accrual
            ('2022-06-30', days, date(2022, 7, 1)),
            # Second accrual
            ('2022-07-01', days + 1, date(2023, 1, 1)),
        ))

    def test_frequency_yearly(self):
        """ Assert number of days and nextcall are computed correctly for a one level yearly accrual plan """
        with freeze_time('2021-09-01'):
            accrual_plan = self.accrual_plan_yearly
            # this sets up an accrual on the 1st of January
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()
            self.assertFalse(allocation.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation.number_of_days, 0, 'There should be no days allocated yet.')

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # The start of the first plan is in the future (tomorrow), nextcall should be False, no accrued days
            ('2021-09-01', 0, False),
            # Assert running the cron again doesn't change anything
            ('2021-09-01', 0, False),
            # One day before the first accrual, nothing changed
            ('2021-12-31', 0, date(2022, 1, 1)),
            # 2021-09-02 -> 2022-01-01: 4 month out of the 6 month of the first period
            ('2022-01-01', days := (29 + 31 + 30 + 31) / 365, date(2023, 1, 1)),
            # One day before the second accrual
            ('2022-12-31', days, date(2023, 1, 1)),
            # Second accrual
            ('2023-01-01', days + 1, date(2024, 1, 1)),
        ))

    def test_check_gain(self):
        """ Assert number of days and nextcall are computed correctly for 2 accrual allocations based on
            one level weekly accrual plans, one of the plan is based on work time, the other isn't
            Also take a leave
        """
        with freeze_time('2021-08-30'):
            attendances = []
            for index in range(5):
                attendances.append((0, 0, {
                    'hour_from': 8,
                    'hour_to': 12,
                    'dayofweek': str(index),
                }))
                attendances.append((0, 0, {
                    'hour_from': 13,
                    'hour_to': 17,
                    'dayofweek': str(index),
                }))
            calendar_emp = self.env['resource.calendar'].create({
                'name': '40 Hours',
                'attendance_ids': attendances,
            })

            # Get the same configuration as 'accrual_plan_based_on_worked_time', except it is not based on working time
            self.accrual_plan_weekly.level_ids[0].added_value = 5

            self.employee_emp.resource_calendar_id = calendar_emp.id
            allocation_not_worked_time = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': self.accrual_plan_weekly.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'state': 'confirm',
            })
            allocation_worked_time = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': self.accrual_plan_based_on_worked_time.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'state': 'confirm',
            })
            allocations = allocation_not_worked_time | allocation_worked_time
            allocations.action_approve()
            work_entry_type = self.work_entry_type_accrual_non_elligible_absence_day_day
            self._create_leave(self.employee_emp, work_entry_type, '2021-09-02', '2021-09-02', validate=True)
            self.assertFalse(allocation_not_worked_time.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertFalse(allocation_worked_time.nextcall, 'There should be no nextcall set on the allocation.')
            self.assertEqual(allocation_not_worked_time.number_of_days, 0, 'There should be no days allocated yet.')
            self.assertEqual(allocation_worked_time.number_of_days, 0, 'There should be no days allocated yet.')

        # Running update on Monday (first accrual day)
        with freeze_time('2021-09-06'):
            self._run_update_accrual_cron()
            # First level starts on 2021-08-31 = Tuesday
            # 6 days out of the 7 days of the week (doesn't take the current day into account = 09-06)
            self.assertAlmostEqual(allocation_not_worked_time.number_of_days, not_work_time_duration := 6 / 7 * 5, 4)
            # Worked 3 days: Tuesday, Wednesday and Friday (Thursday is off: 09-02)
            # Saturday and Sunday aren't in the 'calendar_emp', they don't count
            self.assertAlmostEqual(allocation_worked_time.number_of_days, work_time_duration := 3)
            expected_nextcall = datetime.date(2021, 9, 13)
            self.assertEqual(allocation_not_worked_time.nextcall, expected_nextcall, 'The next call date of the cron should be the September 13th')
            self.assertEqual(allocation_worked_time.nextcall, expected_nextcall, 'The next call date of the cron should be the September 13th')

        # Running update on next Monday (second accrual day)
        with freeze_time('2021-09-13'):
            self._run_update_accrual_cron()
            self.assertAlmostEqual(allocation_not_worked_time.number_of_days, not_work_time_duration + 5, 4, 'There should be 9.2857 days allocated.')
            self.assertAlmostEqual(allocation_worked_time.number_of_days, work_time_duration + 5, 4, 'There should be 8 days allocated.')

            expected_nextcall = datetime.date(2021, 9, 20)
            self.assertEqual(allocation_not_worked_time.nextcall, expected_nextcall, 'The next call date of the cron should be September 20th')
            self.assertEqual(allocation_worked_time.nextcall, expected_nextcall, 'The next call date of the cron should be September 20th')

    def _test_accrual_allocation_number_of_days_with_leave(self, time_off_type, deducted):
        """ Assert number of days and nextcall are computed correctly for a one level daily accrual plan
            while taking a leave that is linked to a `work.entry.type` which is accrual allocation elligible or not
        """
        accrual_plan = self.based_on_work_time_accrual_plan_daily
        with freeze_time('2025-09-01'):  # Monday
            allocation_worked_time = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation_worked_time.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation_worked_time, (
            ('2025-09-01', 0, date(2025, 9, 2)),
            # Saturday: got 10 working days = 10 * 1d
            ('2025-09-13', 10, date(2025, 9, 14)),
        ))

        # Accrual elligible or not depending on the injected time_off_type
        with freeze_time('2025-09-13'):
            self._create_leave(self.employee_emp, time_off_type, '2025-09-16', '2025-09-18', validate=True)

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation_worked_time, {
            # On the next Saturday: got 15 working days deducted or not
            ('2025-09-20', 12 if deducted else 15, date(2025, 9, 21)),
        })

    def test_non_elligible_leaves(self):
        timeoff_type = self.work_entry_type_accrual_non_elligible_absence_day_day
        self._test_accrual_allocation_number_of_days_with_leave(timeoff_type, deducted=True)

    def test_elligible_leaves(self):
        timeoff_eligible_type = self.work_entry_type_accrual_elligible_absence_day_day
        self._test_accrual_allocation_number_of_days_with_leave(timeoff_eligible_type, deducted=False)

    def test_worked_leaves(self):
        remote_work_type = self.work_entry_type_working_time_day_day
        self._test_accrual_allocation_number_of_days_with_leave(remote_work_type, deducted=False)

    def test_check_max_value(self):
        """ Assert number of days and nextcall are compted correctly for a one level accrual plan
            with a maximum number of leave set to 1
        """
        accrual_plan = self.accrual_plan_daily_end_max_1_leave
        with freeze_time("2017-12-05"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2017-12-05', 0, False),
            # The plan only starts one day after the start of the allocation
            ('2017-12-07', 1, date(2017, 12, 8)),
            # Max number of days is reached
            ('2017-12-08', 1, date(2017, 12, 9)),
            ('2017-12-09', 1, date(2017, 12, 10)),
        ))

    def test_check_max_value_hours(self):
        """ Assert number of days and nextcall are compted correctly for a one level accrual plan
            with a maximum number of leave set to 1, and with ''added_value_type' set to 'hour'
        """
        with freeze_time("2017-12-05"):
            accrual_plan = self.accrual_plan_daily_1_hour_4_max_leave
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # First level start date is in the future (tomorrow), nextcall isn't set
            ('2017-12-05', 0, False),
            # The plan only starts one day after the start of the allocation
            ('2017-12-07', 0.125, date(2017, 12, 8)),
            # Assert the maximum leave is respected (4h = 0.5 day here)
            ('2017-12-17', 0.5, date(2017, 12, 18)),
        ))

    @freeze_time("2024-10-10")
    def test_accrual_hours_with_max_carryover(self):
        """ Assert get_allocation_data returns a correct number of allocated hours / remaining leaves
            for an accrual allocation with a monthly accrual plan that only carryover a limited number
            of hours
        """
        accrual_plan = self.accrual_plan_monthly_31th_max_carryover_duration
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
            'name': 'Accrual allocation for employee',
            'date_from': datetime.date(2025, 1, 1),
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 0,
        })
        allocation.action_approve()

        hours_per_day = self.employee_emp.resource_calendar_id.hours_per_day
        # The first month covers 2025-01-02 -> 2025-01-31 (29 days)
        first_period_allocated_duration = 29 / 31 / hours_per_day
        self._assert_get_allocation_data_future(allocation, (
            # As the plan still hasn't started yet, assert allocated_duration is 0
            ('2024-10-10', 0),
            # One day before the last day of the first period
            ('2025-01-30', 0),
            # First accrual happens at the end of the period (2025-01-31)
            ('2025-01-31', first_period_allocated_duration),
            # + the next 10 month of accrual (10 * 1 hour)
            ('2025-12-02', first_period_allocated_duration + 10 / hours_per_day),
            # Carryover only keeps 4 hours on "2025-01-01" + January accrual (1 hour)
            ('2026-02-15', 5 / hours_per_day),
        ))

    def _assert_current_level(self, allocation, assertions):
        for target_date, expected_level in assertions.items():
            accrual_plan_level = allocation._get_current_accrual_plan_level_idx(parse_iso_date(target_date))[0]
            self.assertEqual(accrual_plan_level, expected_level)

    @freeze_time("2017-12-05")
    def test_accrual_transition_immediately(self):
        """ Test transition mode 'immediately' """
        # 1 accrual with 2 levels and level transition immediately
        accrual_plan = self.accrual_plan_2_lvls_weekly
        accrual_plan.transition_mode = 'immediately'
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 0,
        })
        allocation.action_approve()
        first_level, second_level = self.accrual_plan_2_lvls_weekly.level_ids
        self._assert_current_level(allocation, {
            '2017-12-05': None,
            # The first level starts 1 day after the date_from of the allocation: 2017-12-06
            '2017-12-06': first_level,
            '2017-12-14': first_level,
            # The second level starts 10 days after the date_from of the allocation: 2017-12-15
            '2017-12-15': second_level,
            '2018-01-01': second_level,
        })

    @freeze_time("2025-07-08")
    def test_accrual_transition_after_period(self):
        """ Test transition mode 'end_of_accrual' """
        accrual_plan = self.accrual_plan_2_lvls_weekly
        accrual_plan.transition_mode = 'end_of_accrual'
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 0,
        })
        allocation.action_approve()
        first_level, second_level = accrual_plan.level_ids
        # Second level starts on 2025-07-18 (10 days later), but the 'transition_mode' is set to 'end_of_accrual',
        # so the first level will "end its period" before transition
        # ===> 2025-07-18 is a Friday, therefore the second level will start on 2025-07-21 (next Monday)
        self._assert_current_level(allocation, {
            '2025-07-08': None,
            # The first level starts 1 day after the date_from of the allocation: 2025-07-09
            '2025-07-09': first_level,
            # Theoritical level transition
            '2025-07-18': first_level,
            # Last day before level transition
            '2025-07-20': first_level,
            '2025-07-21': second_level,
            '2026-01-01': second_level,
        })

    def test_unused_accrual_lost(self):
        """ Assert the allocated days are reset on carryover while the maximum number of leave is reached """
        with freeze_time('2021-12-15'):
            accrual_plan = self.accrual_plan_daily_carryover_lost
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 10,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # 31 - 16 = 15 * 1 accrued days + the initial number of days > max number of days which is 20
            ('2021-12-31', 20, date(2022, 1, 1)),
            # Carryover reset
            ('2022-01-01', 1, date(2022, 1, 2)),
            ('2022-01-05', 5, date(2022, 1, 6)),
        ))

    def test_unused_accrual_carried_over_2(self):
        """ Assert the allocated duration is unchanged on carryover when the accrual plan carryover policy is 'limited'
            and that the allocated duration is under this amount on carryover date
        """
        with freeze_time('2021-01-01'):
            accrual_plan = self.accrual_plan_yearly_carryover_limited_10
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 8,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2021-12-31', 8, date(2022, 1, 1)),
            # First accrual happens
            ('2022-01-01', 10, date(2023, 1, 1)),
            # One day before the second accrual
            ('2022-12-31', 10, date(2023, 1, 1)),
            # Second accrual happens
            ('2023-01-01', 12, date(2024, 1, 1)),
            # 10 carriedover days + 2 accrued days for the past year
            ('2024-01-01', 12, date(2025, 1, 1)),
        ))

    def test_unused_accrual_carried_over_limit(self):
        """ Assert the number of days and the nextcall are computed correctly for an accrual allocation with:
            - Initial number of days set to 10
            - Daily accrual of 1 day
            - Accrues at the start of the period
            - Maximum of 25 leaves
            - Carryover limited to 15 days at year_start
        """
        with freeze_time('2021-12-15'):
            accrual_plan = self.accrual_plan_daily_max_leave_carryover_limited
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 10,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Nextcall unset because the start of the first level is in the future
            ('2021-12-15', 10, False),
            # First level start: nextcall should be set + first accrual
            ('2021-12-16', 11, date(2021, 12, 17)),
            # Last day before carryover
            ('2021-12-31', 25, date(2022, 1, 1)),
            # Assert max 15 days were carriedover + accrual of the first day of the year
            ('2022-01-01', 16, date(2022, 1, 2)),
        ))

    def test_period_prorata(self):
        """ Assert the number of days and the nextcall are computed correctly for an accrual allocation with:
            - Initial number of days set to 10
            - Accrues at the end of the period
            - With a level:
                - Starts at allocation
                - Accrues daily of 15 day
            - With another level:
                - Starts 4 months after the allocation (date_from)
                - Accrues biyearly of 10 days
        """
        accrual_plan = self.accrual_plan_biyearly_2_levels
        with freeze_time('2020-08-16'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual Allocation - Test',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        first_period_total_days = self._get_period_days('2020-07-01', '2020-12-31')
        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Level transition -> accrual for the period using the first level
            ('2020-12-16', duration := 15 * self._get_period_days('2020-08-16', '2020-12-15') / first_period_total_days, date(2021, 1, 1)),
            # Second level accrual: same period from 2020-07-01 to 2020-12-31
            ('2021-01-01', duration := duration + 10 * self._get_period_days('2020-12-16', '2020-12-31') / first_period_total_days, date(2021, 7, 1)),
            # Second level accrual: 10 (for period 2021-01-01 - 2021-06-30)
            ('2021-07-01', duration := duration + 10, date(2022, 1, 1)),
            # Second level accrual: 10 (for period 2021-07-01 - 2021-12-31)
            ('2022-01-01', duration + 10, date(2022, 7, 1)),
        ))

    def test_maximum_leaves_three_levels_accrual(self):
        """ Assert number of days respects the level maximum leaves with 3 levels having different
            'maximum_leaves' config for each level: 3 for the first level, 6 for the second and
            no limit for the third one
        """
        accrual_plan = self.accrual_plan_3_levels_monthly_max_leaves
        with freeze_time('2022-01-31'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual Allocation - Test',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 2,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2022-01-31', 2, False),
            # One day before the start of the first level
            ('2022-03-30', 2, False),
            # First level starts, nextcall set, 0 days accrued as the day are accrued at the end of the period
            ('2022-03-31', 2, date(2022, 4, 30)),
            # First period accrual, use the first level policy for the maximum leaves (3 days)
            ('2022-04-30', 3, date(2022, 5, 31)),
            # First period of the second level and also the third level transition
            # Use the second level policy for the maximum leaves (6 days)
            ('2022-05-31', 6, date(2022, 6, 30)),
            # One day before the next accrual
            ('2022-06-29', 6, date(2022, 6, 30)),
            # Third level first period: it's now uncapped !
            ('2022-06-30', 7, date(2022, 7, 31)),
        ))

    def test_accrual_yearly_on_carryover_lost(self):
        accrual_plan = self.accrual_plan_yearly_carryover_lost
        with freeze_time('2019-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual Allocation - Test',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # First level starts immediately, accruing 3 days for the year
            ('2019-01-01', 3, date(2020, 1, 1)),
            ('2019-12-31', 3, date(2020, 1, 1)),
            # All days lost on carryover, then the yearly accrual happens
            ('2020-01-01', 3, date(2021, 1, 1)),
        ))

    def test_accrual_leaves_taken_maximum(self):
        """ Assert the `maximum_leave` is respected for an accrual allocation while taking a 5 days leave """
        accrual_plan = self.accrual_plan_weekly_5_max_leave
        # Creating the allocation on a Saturday
        with freeze_time("2022-01-01"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2022-01-01', 0, date(2022, 1, 3)),
            # First accrual for Saturday and Sunday out of the 7 days of the week
            ('2022-01-03', days := 2 / 7, date(2022, 1, 10)),
            ('2022-01-10', days + 1, date(2022, 1, 17)),
            # Maximum reached after 5 weeks of accrual
            ('2022-02-28', 5, date(2022, 3, 7)),
        ))

        # 5 days leave
        self._create_leave(self.employee_emp, self.work_entry_type, '2022-03-07', '2022-03-11', validate=True)

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2022-06-01', 10, date(2022, 6, 6)),
        ))

    def test_accrual_leaves_taken_maximum_hours(self):
        """ Assert the max amount of leave is respected for an accrual allocation which adds 3 hours weekly """
        accrual_plan = self.accrual_plan_weekly_hour_max_leaves
        with freeze_time('2022-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type_hour.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2022-01-01', 0, date(2022, 1, 3)),
            # Monday: first accrual for Saturday and Sunday out of the 7 days of the week
            ('2022-01-03', (2 / 7 * 3) / self.hours_per_day, date(2022, 1, 10)),
            # Max number of leave reached (10 hours)
            ('2022-03-06', 10 / self.hours_per_day, date(2022, 3, 7)),
        ))

        with freeze_time('2022-03-06'):
            self._create_leave(self.employee_emp, self.work_entry_type_hour, '2022-03-07', '2022-03-07', validate=True)

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Should accrue 8 more hours (the maximum is reached once again)
            ('2022-06-01', 18 / self.hours_per_day, date(2022, 6, 6)),
        ))

    @mute_logger('odoo.sql_db')
    def test_yearly_cap_constraint(self):
        accrual_plan = self.accrual_plan_daily_5_max_leaves
        with self.assertRaises(IntegrityError):
            accrual_plan.level_ids[0].write({
                'cap_accrued_time_yearly': True,
                'maximum_leave_yearly': 0,
            })
        accrual_plan.level_ids[0].write({
            'cap_accrued_time_yearly': True,
            'maximum_leave_yearly': 1,
        })
        accrual_plan.level_ids[0].write({
            'cap_accrued_time_yearly': False,
            'maximum_leave_yearly': 0,
        })
        self.env.cr.precommit.run()
        self.env.flush_all()

    def test_yearly_cap(self):
        """ Assert combining `maximum_leave_yearly` and a `maximum_leave` works properly """
        work_entry_type = self.work_entry_type_absence_hour_hour
        accrual_plan = self.accrual_plan_hourly_max_leaves_capped_yearly

        with freeze_time('2024-12-25'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': work_entry_type.id,
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 0,
            })

        assertion_structure = {
            'number_of_days': 'float',
            'allocated_duration': 'float',
            'remaining_leaves': 'float',
        }
        self._assert_get_allocation_data(allocation, (
            # Assert yearly cap is respected (16 hours max)
            ('2024-12-31', 16 / self.hours_per_day, 16, 16),
        ), assertion_structure)

        with freeze_time('2024-12-30'):
            leave = self._create_leave(self.employee_emp, work_entry_type, '2024-12-27', '2024-12-27', 10, 12)
            self.assertEqual(allocation.leaves_taken, 2)
            self.assertEqual(leave.number_of_hours, 2)

        self._assert_get_allocation_data(allocation, (
            # Nothing more accrued because the yearly cap is reached
            ('2024-12-31', 16 / self.hours_per_day, 16, 14),
            # Assert the maximum leave is respected: the number_of_days is 24 (max available leaves) + 2 hours of the leave
            ('2025-01-06', 26 / self.hours_per_day, 26, 24),
        ), assertion_structure)

    @freeze_time("2023-04-24")
    def test_accrual_period_start(self):
        """ Assert everything goes smoothly when changing the accrual plan accruad gain time and then creating another,
            Running test on a Monday
        """
        accrual_plan = self.accrual_plan_weekly_5_max_leave
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 0,
        })
        allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Accruals should happen at the end of the period, on the next Monday
            ("2023-04-24", 0, date(2023, 5, 1)),
        ))

        with Form(accrual_plan) as plan_form:
            plan_form.accrued_gain_time = 'start'

        allocation = self._create_form_test_accrual_allocation(self.work_entry_type, '2023-04-24',
            self.employee_emp, accrual_plan, creator_user=self.user_hrmanager_id)
        allocation.action_approve()
        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Accruals happens at the start of the first level
            ("2023-04-24", 1, date(2023, 5, 1)),
        ))

    def test_accrual_period_start_multiple_runs(self):
        accrual_plan = self.accrual_plan_monthly_start_15_max_leaves
        with freeze_time("2023-12-25"):
            allocation = self._create_form_test_accrual_allocation(self.work_entry_type,
                '2023-12-25', self.employee_emp, accrual_plan, creator_user=self.user_hrmanager_id)
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2023-12-25', days := self._get_period_days('2023-12-25', '2024-01-12') / self._get_period_days('2023-12-13', '2024-01-12') * 1.5, date(2024, 1, 1)),
            # Carryover date, nothing happens
            ('2024-01-01', days, date(2024, 1, 13)),
            # One day before the accrual, nothing happens
            ('2024-01-12', days, date(2024, 1, 13)),
            # Accruals for the first month
            ('2024-01-13', days + 1.5, date(2024, 2, 13)),
            # Maximum number of leave is reached
            ('2024-05-13', 4, date(2024, 6, 13)),
        ))

    def test_accrual_period_start_level_transfer(self):
        """ Assert maximum number of leave is respected when there are 2 levels that are capped and that have different number
            of maximum leaves
        """
        accrual_plan = self.accrual_plan_2_lvls_start_weekly_max_leaves
        # On a Wednesday
        with freeze_time("2023-04-26"):
            allocation = self._create_form_test_accrual_allocation(
                self.work_entry_type, '2023-04-26', self.employee_emp, accrual_plan, creator_user=self.user_hrmanager_id)
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Accrual for the entire week
            ("2023-04-26", 1, date(2023, 5, 3)),
            # One day before level transition
            # Assert maximum available leave of the first level is respected
            ("2023-07-25", 8, date(2023, 7, 26)),
            # Assert the maximum available leave of the second level is respected
            ("2023-07-26", 5, date(2023, 8, 2)),
        ))

    def test_accrual_carryover_at_allocation(self):
        """ Assert the allocated days are lost on carryover date for an allocation with a accrual plan
            which accrued gain time is 'start'
        """
        accrual_plan = self.accrual_plan_monthly_start_carryover_allocation_lost
        with freeze_time("2023-04-26"):
            allocation = self._create_form_test_accrual_allocation(self.work_entry_type, '2023-04-26', self.employee_emp, accrual_plan)
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ("2023-04-26", days := 1 / self._get_period_days('2023-04-26', '2023-05-26'), date(2023, 4, 27)),
            ("2023-04-27", days := days + 1, date(2023, 5, 27)),
            # Last accrual before the carryoverdate, nextcall is the next carryover date
            ("2024-03-27", days := days + 11, date(2024, 4, 26)),
            # Carryover date happens
            ("2024-04-26", 0, date(2024, 4, 27)),
            # First accrual after the carryover date
            ("2024-04-27", 1, date(2024, 5, 27)),
            # Accruals keep on going...
            ("2024-07-27", 4, date(2024, 8, 27)),
        ))

    def test_accrual_carryover_at_other(self):
        """ Assert an allocation behaves nicely when creating it on the day of its carryover (using carryover_date: other)
            with a limited amount of carriedover days
        """
        accrual_plan = self.accrual_plan_monthly_start_max_69_carriedover
        with freeze_time("2023-04-20"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'date_from': '2023-04-20',
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Accrual at the start of the first level
            ("2023-04-20", days := (30 - 20 + 1 + 10) / (30 - 11 + 1 + 10) * 10, date(2023, 5, 11)),
            # Second accrual for an entire month
            ("2023-05-11", days + 10, date(2023, 6, 11)),
            # Carryover date: assert maximum number of leave is taken into account
            ("2024-04-20", days := 69, date(2024, 5, 11)),
            # Accruals keep on going...
            ("2024-05-11", days := days + 10, date(2024, 6, 11)),
            ("2024-06-11", days + 10, date(2024, 7, 11)),
        ))

    def test_accrual_carrover_other_period_end_multi_level(self):
        """ Assert the allocated days are computed correctly for a 3 levels accrual allocation
            that uses different maximum number of leave and carryover policy for each level
        """
        accrual_plan = self.accrual_plan_3_lvls_monthly_biyearly_yearly_carryover_policy_change
        with freeze_time("2023-04-04"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 9,
                'date_from': '2023-04-04',
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ("2023-04-04", 9, False),
            # Start of the first level
            ("2023-04-09", 9, date(2023, 5, 9)),
            # End of the first period of the first level: accrual happens
            ("2023-05-09", 10, date(2023, 6, 5)),
            # Carryover date: nothing changes
            ("2023-06-05", 10, date(2023, 6, 9)),
            # Accruals keep on going...
            ("2023-06-09", 11, date(2023, 7, 9)),
            # Day of the level transition, accrual of the last period of the first level
            # Maximum leaves of the first level reached
            ("2024-01-04", 15, date(2024, 2, 17)),
            # Second level first accrual
            ("2024-02-17", 10, date(2024, 6, 5)),
            # Carryover date: nothing changes
            ("2024-06-05", 10, date(2024, 9, 4)),
            # Level transition of the third level
            # The allocated duration is the same because of the maximum of the second level
            ("2024-09-04", 10, date(2025, 6, 5)),
            # All days are lost on carryover
            ("2025-06-05", 0, date(2025, 7, 15)),
            # First accrual for the third level
            ("2025-07-15", self._get_period_days("2024-09-04", "2025-07-14") / self._get_period_days("2024-07-15", "2025-07-14") * 12, date(2026, 6, 5)),
        ))

    @freeze_time('2023-09-01')
    def test_accrual_creation_on_anterior_date(self):
        accrual_plan = self.accrual_plan_weekly_carryover_lost
        accrual_allocation = self.env['hr.leave.allocation'].new({
            'name': 'Employee allocation',
            'work_entry_type_id': self.work_entry_type.id,
            'date_from': '2023-01-01',
            'employee_id': self.employee_emp.id,
            'accrual_plan_id': accrual_plan.id,
        })
        # As the duration is set to a onchange, we need to force that onchange to run
        accrual_allocation._onchange_process_accrual_plans()
        accrual_allocation.action_approve()
        # The amount of days should be computed as if it was accrued since
        # the start date of the allocation.
        self.assertAlmostEqual(accrual_allocation.number_of_days, 34.0, places=0)
        self.assertFalse(accrual_allocation.last_accrual == accrual_allocation.date_from)
        self._run_update_accrual_cron()
        # The amount being already computed, the amount should stay the same after the cron
        # running on the same day.
        self.assertAlmostEqual(accrual_allocation.number_of_days, 34.0, places=0)

    @freeze_time("2023-12-31")
    def test_future_accrual_time(self):
        """ Check that the carryover is processed correctly when the 'added_value_type' is set to 'hour' """
        work_entry_type = self.work_entry_type_absence_hour_hour
        accrual_plan = self.accrual_plan_monthly_hour
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': work_entry_type.id,
            'number_of_days': 1 / self.hours_per_day,
        })
        allocation.action_approve()
        self._assert_get_allocation_data_future(allocation, (
            # First level starts on 2024-01-01 and first period end is 2024-02-01
            ('2024-01-01', 1, 1),
            # Accruals keep going on monthly...
            ('2024-02-01', 2, 2),
            ('2024-03-01', 3, 3),
        ))
        self._create_leave(self.employee_emp, work_entry_type, '2024-02-05', '2024-02-05', 10, 11)
        self._assert_get_allocation_data_future(allocation, (
            ('2024-01-01', 1, 1),
            ('2024-02-01', 2, 2),
            # The 1 day leave is taken into account, the remaining leaves should decrease
            ('2024-02-05', 2, 1),
            ('2024-03-01', 3, 2),
        ))

    def test_added_type_during_onchange(self):
        """ The purpose is to test whether the value of the `added_value_type`
            field is correctly propagated from the first level to the second
            during creation on the dialog form view.
        """
        accrual_plan = self.accrual_plan_monthly_carryover_all
        # Simulate the onchange of the dialog form view
        # Trigger the `_compute_added_value_type` method (with virtual records)
        form = Form(accrual_plan)
        with form.level_ids.new() as level:
            self.assertEqual(level.added_value_type, 'hour')

    @freeze_time('2024-03-02')
    def test_accrual_creation_for_history(self):
        """ Assert modifying the form fields of an accrual allocation updates the `number_of_days` properly """
        with Form(self.env['hr.leave.allocation'], 'hr_holidays.hr_leave_allocation_view_form_manager') as form:
            form.name = 'Test accrual allocation'
            form.accrual_plan_id = self.accrual_plan_monthly_end_carry_over_lost_year_start
            form.employee_id = self.employee_emp
            form.work_entry_type_id = self.work_entry_type
            form.date_from = '2024-03-01'
            self.assertEqual(form.number_of_days, 0)
            form.date_from = '2023-01-01'
            # All days are lost on 2024-01-01, then 2 accrual for Jan. and Feb.
            self.assertEqual(form.number_of_days, 2)
            form.date_to = '2023-12-31'
            # The allocation stops 1 day before the carryover date
            # 11 month accrual + 30 days out of 31 days of December 2023 (because the accrual happens on the 31th of the month)
            self.assertEqual(form.number_of_days, 11 + 30 / 31)

            form.number_of_days_display = 0
            self.assertEqual(form.number_of_days_display, 0)

        allocation = form.record
        self.assertEqual(allocation.number_of_days, 0)

        with Form(allocation, 'hr_holidays.hr_leave_allocation_view_form_manager') as form:
            form.accrual_plan_id = self.accrual_plan_weekly_hour_max_leaves
            self.assertEqual(form.type_request_unit, 'hour')
            form.date_from = '2023-11-01'
            # Max amount of allocated duration is reached (10h)
            self.assertEqual(form.number_of_days, 10 / self.hours_per_day)

            form.number_of_hours_display = 0
            self.assertEqual(form.number_of_hours_display, 0)

        self.assertEqual(allocation.number_of_days, 0)

        with Form(allocation, 'hr_holidays.hr_leave_allocation_view_form_manager') as form:
            form.work_entry_type_id = self.work_entry_type_hour
            self.assertEqual(form.number_of_days, 0)

            form.date_from = '2024-01-01'
            form.date_to = False
            # Max amount of allocated duration is reached (10h)
            self.assertEqual(form.number_of_days, 10 / self.hours_per_day)

            form.number_of_hours_display = 5
            self.assertEqual(form.number_of_hours_display, 5)
        self.assertEqual(allocation.number_of_days, 5 / self.hours_per_day)
        allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # On next Monday
            ('2024-03-04', 8 / self.hours_per_day, date(2024, 3, 11)),
            # Next Monday, max amount of allocated duration is reached
            ('2024-03-11', 10 / self.hours_per_day, date(2024, 3, 18)),
        ))

    def test_accrual_period_start_past_start_date(self):
        """ Assert the `number_of_days` of an accrual allocation created in the past is computed properly """
        accrual_plan = self.accrual_plan_monthly_start_carryover_year_start
        accrual_plan.level_ids[0].write({
            'added_value': 1,
            'first_day': 1,
        })
        with freeze_time('2024-03-01'):
            accrual_allocation = self._create_form_test_accrual_allocation(self.work_entry_type, '2024-01-01', self.employee_emp, accrual_plan, creator_user=self.user_hrmanager)
            accrual_allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(accrual_allocation, (
            # 3 months elapsed: 3 times accrued
            ('2024-03-01', 3, date(2024, 4, 1)),
            # Accruals keep on going...
            ('2024-04-01', 4, date(2024, 5, 1)),
        ))

    def test_cancel_invalid_leaves_with_regular_and_accrual_allocations(self):
        """ Assert `hr.leave._cancel_invalid_leaves` doesn't change the `state` of a valid leave
            covered by an accrual allocation
        """
        accrual_plan = self.accrual_plan_monthly_start_carryover_year_start
        accrual_plan.level_ids[0].write({
            'added_value': 1,
            'first_day': 1,
        })
        allocations = self.env['hr.leave.allocation'].create([{
                'name': 'Regular allocation',
                'date_from': '2024-05-01',
                'work_entry_type_id': self.work_entry_type.id,
                'employee_id': self.employee_emp.id,
                'number_of_days': 2,
            }, {
                'name': 'Accrual allocation',
                'date_from': '2024-05-01',
                'work_entry_type_id': self.work_entry_type.id,
                'employee_id': self.employee_emp.id,
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 3,
            },
        ])
        allocations.action_approve()

        leave = self._create_leave(self.employee_emp, self.work_entry_type, '2024-05-13', '2024-05-17', validate=True)

        with freeze_time('2024-05-06'):
            self.env['hr.leave']._cancel_invalid_leaves()
        self.assertEqual(leave.state, 'validate', "Leave must not be canceled")

    @freeze_time("2024-01-01")
    def test_accrual_leaves_cancel_cron(self):
        """ Assert `hr.leave._cancel_invalid_leaves` changes the `state` of a leave that is not affordable
            by an accrual plan, taking the `work.entry.type` `allows_negative` parameter into account
        """
        accrual_plan = self.accrual_plan_period_end_montlhy_max_carryover_year_start
        self.env['hr.leave.allocation'].create([{
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type_no_negative.id,
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 1,
            }, {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type_negative.id,
                'accrual_plan_id': accrual_plan.id,
                'number_of_days': 1,
            },
        ])

        excess_leave = self._create_leave(self.employee_emp, self.work_entry_type_no_negative, '2024-01-05', '2024-01-05')
        allowed_negative_leave = self._create_leave(self.employee_emp, self.work_entry_type_negative, '2024-01-12', '2024-01-12')

        # As accrual allocation don't take into account future leaves,
        # it should be possible to take both leaves.
        self._create_leave(self.employee_emp, self.work_entry_type_no_negative, '2024-01-04', '2024-01-04')
        self._create_leave(self.employee_emp, self.work_entry_type_negative, '2024-01-11', '2024-01-11')
        self.env.flush_all()

        self.env['hr.leave']._cancel_invalid_leaves()

        # Since both leave are outside an allocation validity,
        # they are detected as discrepancies. However, the
        # leave that is not exceeding the negative amount should be kept
        # as it is valid according to the configuration.
        self.assertEqual(excess_leave.state, 'cancel')
        self.assertEqual(allowed_negative_leave.state, 'validate')

        self._create_leave(self.employee_emp, self.work_entry_type_negative, '2024-01-10', '2024-01-10')

        self.env['hr.leave']._cancel_invalid_leaves()

        # The last added leave creates a discrepancy that exceeds the
        # maximum amount allowed in negative.
        self.assertEqual(allowed_negative_leave.state, 'cancel')

    @freeze_time("2024-03-01")
    def test_future_accural_time_with_leaves_taken_in_the_past(self):
        work_entry_type = self.work_entry_type_day
        accrual_plan = self.accrual_plan_daily_start_max_leaves_carryover_year_start

        allocation = self._create_form_test_accrual_allocation(
            work_entry_type, '2024-02-01', self.employee_emp, accrual_plan, creator_user=self.user_hrmanager)

        self._assert_get_allocation_data_future(allocation, (
            # The available leaves maximum is reached
            ('2024-03-01', 10, 10),
        ))
        self._create_leave(self.employee_emp, work_entry_type, '2024-02-26', '2024-03-01', validate=True)
        self._assert_get_allocation_data_future(allocation, (
            # Only 5 days left
            ('2024-03-01', 10, 5),
            ('2024-03-02', 11, 6),
            ('2024-03-03', 12, 7),
            ('2024-03-04', 13, 8),
            # The available leaves maximum is reached again
            ('2024-03-10', 15, 10),
        ))
        # 5 days leave (the 4th is a Monday)
        self._create_leave(self.employee_emp, work_entry_type, '2024-03-04', '2024-03-08', validate=True)
        self._assert_get_allocation_data_future(allocation, (
            # Only 5 hours left
            ('2024-03-04', 13, 3),
            # The available leaves maximum is reached again
            ('2024-03-11', 20, 10),
        ))

    @freeze_time('2024-01-01')
    def test_validate_leaves_with_more_days_than_allocation(self):
        """ Assert taking leave without having enough allocation raises error """
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 1,
        })

        allocation.action_approve()
        # Should explode because the allocation doesn't give enough day to cover the entire leave
        with self.assertRaisesRegex(ValidationError, ' does not have a valid allocation for the leave type '):
            self._create_leave(self.employee_emp, self.work_entry_type, '2024-01-09', '2024-01-12')

        # Number of days given by the allocation is 1 -> enough credits -> no error
        leave = self._create_leave(self.employee_emp, self.work_entry_type, '2024-01-09 08:00:00', '2024-01-09 17:00:00', validate=True)

        leave.action_refuse()
        leave.write({
            'request_date_from': '2024-01-09',
            'request_date_to': '2024-01-12',
        })
        # Should explode because the allocation doesn't give enough day to cover the entire leave
        with self.assertRaisesRegex(ValidationError, ' does not have a valid allocation for the leave type '):
            leave.action_approve()

    def test_compute_allocation_days_after_adding_employee(self):
        """ Assert changing the employee of an accrual allocation updates the `number_of_days`
            according to its attendances (with a plan based on work time)
        """
        accrual_plan = self.accrual_plan_daily_carryover_year_start_all_work_time

        with freeze_time('2024-08-19'):
            attendances = []
            for index in range(3):
                attendances.extend([
                    (0, 0, {
                        'hour_from': 8,
                        'hour_to': 10,
                        'dayofweek': str(index),
                    }),
                    (0, 0, {
                        'hour_from': 11,
                        'hour_to': 13,
                        'dayofweek': str(index),
                    }),
                ])
            calendar_emp = self.env['resource.calendar'].create({
                'name': '20 Hours',
                'attendance_ids': attendances,
            })
            self.employee_hrmanager.resource_calendar_id = calendar_emp.id
            accrual_allocation = self._create_form_test_accrual_allocation(
                self.work_entry_type, '2024-08-07', self.employee_emp, accrual_plan, creator_user=self.user_hrmanager)
            # First level starts on 08-08, which is a Thursday, so the guy gets 2 days for that week (Thursday and Friday),
            # plus 5 days for the next week ('til 08-17 included which is a Friday)
            self.assertEqual(accrual_allocation.number_of_days, 7.0)

            with Form(accrual_allocation) as alloc_form:
                alloc_form.employee_id = self.employee_hrmanager

            # Only 3 days of attendances for the second week of August for that employee: 12, 13 and 14
            self.assertEqual(accrual_allocation.number_of_days, 3.0)

    def test_matching_carryover_and_level_transition_dates(self):
        """ Assert number_of_days computation is correct for an accrual allocation having 2 levels and
            the carryover (days are lost) happens on level transition
        """
        accrual_plan = self.accrual_plan_2_lvls_yearly_carryover_lost
        with freeze_time('2024-01-01'):
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'accrual_plan_id': accrual_plan.id,
            })
            allocation.action_approve()

        year_2025_days = self._get_period_days("2025-01-01", "2025-12-31")
        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2024-01-01', 0, date(2024, 7, 1)),
            # Carryover happens, nothing changes
            ('2024-07-01', 0, date(2025, 1, 1)),
            # Yearly accrual happens
            ('2025-01-01', 12, date(2025, 7, 1)),
            # Level transition happens: accrues for the last period of the first level
            ('2025-07-01', days := self._get_period_days("2025-01-01", "2025-06-30") / year_2025_days * 12, date(2026, 1, 1)),
            # Accrues for the period beginning at the start of the second level up to now
            ('2026-01-01', days + self._get_period_days("2025-07-01", "2025-12-31") / year_2025_days * 14, date(2026, 7, 1)),
        ))

    def test_accrual_plan_with_multiple_levels(self):
        """ Assert the carryover policy of the levels of the accrual allocation are applied correctly (lost then limited)
            for a 2 levels accrual allocation
        """
        accrual_plan = self.accrual_plan_2_lvls_monthly_carryover_lost_limited
        with freeze_time('2024-01-01'):
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
                'accrual_plan_id': accrual_plan.id,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2024-01-01', 1, date(2024, 2, 1)),
            ('2024-05-01', 5, date(2024, 6, 1)),
            # Carryover (days are lost) + accrual for the following month
            ('2024-06-01', 1, date(2024, 7, 1)),
            # Accruals keep on going...
            ('2024-07-01', 2, date(2024, 8, 1)),
            ('2024-08-01', 3, date(2024, 9, 1)),
            ('2024-09-01', 4, date(2024, 10, 1)),
            # On level transition
            # First accrual of the second plan: use the second level 'added_value'
            ('2024-10-01', 6, date(2024, 11, 1)),
            ('2025-05-01', 6 + 7 * 2, date(2025, 6, 1)),
            # Carryover happens, 5 days are kept + accrual for the following month
            ('2025-06-01', 5 + 2, date(2025, 7, 1)),
        ))

    def test_accrual_plan_with_multiple_levels_2(self):
        """ Assert the carryover policy of the levels of the accrual allocation are applied correctly (lost then all)
            for a 2 levels accrual allocation
        """
        accrual_plan = self.accrual_plan_2_lvls_start_yearly_carryover_lost_all
        with freeze_time('2024-01-01'):
            allocation = self._create_form_test_accrual_allocation(self.work_entry_type, '2024-01-01', self.employee_emp, accrual_plan)
            allocation.action_approve()

        year_2026_days = self._get_period_days('2026-01-01', '2026-12-31')
        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # First level directly starts and accrues for the next year
            ('2024-01-01', 10, date(2024, 6, 1)),
            # All days lost on carryover date
            ('2024-06-01', 0, date(2025, 1, 1)),
            # Accrual for year 2025
            ('2025-01-01', 10, date(2025, 6, 1)),
            ('2025-06-01', 0, date(2026, 1, 1)),
            # Accrual 'til the next level transition
            ('2026-01-01', self._get_period_days('2026-01-01', '2026-08-31') / year_2026_days * 10, date(2026, 6, 1)),
            ('2026-06-01', 0, date(2026, 9, 1)),
            ('2026-09-01', days := self._get_period_days('2026-09-01', '2026-12-31') / year_2026_days * 12, date(2027, 1, 1)),
            ('2027-01-01', days + 12, date(2027, 6, 1)),
        ))

    def test_carried_over_days_expiry_date_computation(self):
        """ Assert days expiration correctly behaves with a 2 levels accrual allocation
        """
        accrual_plan = self.accrual_plan_2_lvls_biyearly_expiring
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        year_2024_first_period_days = self._get_period_days('2024-01-01', '2024-06-30')
        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Start of the first level, days will be accrued at the end of the period
            ('2023-01-01', 0, date(2023, 4, 1)),
            # Carryover date, nothing changes
            ('2023-04-01', 0, date(2023, 7, 1)),
            # Accrual for the first half of the year
            ('2023-07-01', 10, date(2023, 9, 1)),
            # Days expire 5 months after the carryover date
            ('2023-09-01', 10, date(2024, 1, 1)),
            # Second accrual for the second half of the year
            ('2024-01-01', days := 20, date(2024, 2, 1)),
            # Level transition: accrual for 1 month out of the 6 month of the first half of the year
            ('2024-02-01', days := days + self._get_period_days('2024-01-01', '2024-01-31') /
                year_2024_first_period_days * 10, date(2024, 4, 1)),
            # Carryover date, nothing changes
            ('2024-04-01', days, date(2024, 6, 1)),
            # Days now expire 2 months later
            ('2024-06-01', 0, date(2024, 7, 1)),
            # Accrual for the left 5 months of the first half of the year
            ('2024-07-01', days := self._get_period_days('2024-02-01', '2024-06-30') /
                year_2024_first_period_days * 15, date(2025, 1, 1)),
            # Second level keeps on going
            ('2025-01-01', days + 15, date(2025, 4, 1)),
        ))

    def test_carried_over_days_expiry_date_computation_3(self):
        """ Assert the expiration date and nextcall of an accrual allocation are computed correctly for
            a 2 levels accrual allocation
        """
        accrual_plan = self.accrual_plan_2_lvls_yearly_monthly_expiring
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_accrual_allocation(allocation, (
                ('2023-01-01', False, date(2023, 5, 1)),
                ('2023-04-30', False, date(2023, 5, 1)),
                # Carryover happens, setting the expiration date in 2 months
                ('2023-05-01', expiration := date(2023, 7, 1), date(2023, 7, 1)),
                # Expiration date: nextcall set to the next accrual
                ('2023-07-01', expiration, date(2024, 1, 1)),
                # Accrual date: nextcall is set to the next carryover
                ('2024-01-01', expiration, date(2024, 5, 1)),
                # One day before carryover: nothing changes
                ('2024-04-30', expiration, date(2024, 5, 1)),
                # Carryover happens, setting the expiration date in 2 months
                ('2024-05-01', expiration := date(2024, 7, 1), date(2024, 7, 1)),
                # Expiration date: nextcall set to the next accrual
                ('2024-07-01', expiration, date(2024, 9, 1)),
                # Level transition: the nextcall is set one month later
                ('2024-09-01', expiration, date(2024, 10, 1)),
                # One day before carryover: nothing changes
                ('2025-04-30', expiration, date(2025, 5, 1)),
                # Carryover date: expiration date is set 3 months later
                ('2025-05-01', date(2025, 8, 1), date(2025, 6, 1)),
            ),
            ('carried_over_days_expiration_date', 'nextcall'),
        )

    def test_carried_over_days_expiry_date_computation_4(self):
        """ Assert the carryover of the accrual allocation is computed correclty
            while modifying the carryover month of the accrual plan
        """
        accrual_plan = self.accrual_plan_monthly_expiring
        with freeze_time('2023-01-15'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        assertions_structure = ('carried_over_days_expiration_date', 'number_of_days', 'nextcall')
        self._assert_accrual_allocation(allocation, (
            ('2023-04-30', False, 4, date(2023, 5, 1)),
            # Carryover date: set the expiration date accordingly
            ('2023-05-01', date(2023, 7, 1), 4, date(2023, 5, 15)),
        ), assertions_structure)

        # The expiration date should be reset because today < carryover < expiration
        with freeze_time('2024-05-01'):
            accrual_plan.carryover_month = '6'

        self._assert_accrual_allocation(allocation, (
            # New carryover date: reset the expiration date
            ('2023-06-01', expiration := date(2023, 8, 1), 5, date(2023, 6, 15)),
            ('2023-06-15', expiration, 6, date(2023, 7, 15)),
            ('2023-07-15', expiration, 7, date(2023, 8, 1)),
            # On carryover date, there was 5 allocated days (make them expire)
            ('2023-08-01', expiration, 2, date(2023, 8, 15)),
            # Accruals keep on going
            ('2023-08-15', expiration, 3, date(2023, 9, 15)),
        ), assertions_structure)

        # Set the carryover to a closer date
        with freeze_time('2023-09-01'):
            accrual_plan.carryover_month = '1'

        self._assert_accrual_allocation(allocation, (
            ('2023-12-15', expiration, 7, date(2024, 1, 1)),
            # New carryover date, expiration date is set
            ('2024-01-01', expiration := date(2024, 3, 1), 7, date(2024, 1, 15)),
            ('2024-01-15', expiration, 8, date(2024, 2, 15)),
            ('2024-02-15', expiration, 9, date(2024, 3, 1)),
            # Expiration date
            ('2024-03-01', expiration, 2, date(2024, 3, 15)),
        ), assertions_structure)

    def test_carried_over_days_expiry(self):
        """ Assert accrual allocation with expiring days + limited number of carriedover days works properly
        """
        accrual_plan = self.accrual_plan_yearly_start_max_carriedover_expiring
        with freeze_time('2024-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Start of the first level
            ('2024-01-01', 10, date(2024, 9, 20)),
            # Carryover date, 5 days are carriedover
            ('2024-09-20', 5, date(2025, 1, 1)),
            # Second accrual for the following year
            ('2025-01-01', 15, date(2025, 1, 20)),
            # Expiration date (5 days are expiring as the allocation had 5 days on carryover date)
            ('2025-01-20', 10, date(2025, 9, 20)),
            # Carryover date, 5 days are carriedover
            ('2025-09-20', 5, date(2026, 1, 1)),
            # Third accrual for the following year
            ('2026-01-01', 15, date(2026, 1, 20)),
            # Expiration date (5 days are expiring as the allocation had 5 days on carryover date)
            ('2026-01-20', 10, date(2026, 9, 20)),
        ))

    @freeze_time('2024-01-01')
    def test_time_off_using_expiring_carried_over_days(self):
        """ Assert get_allocation_data compute future balance properly
            Also assert number of days and nextcall are computed properly for an accrual plan with 2 levels,
            a limited carriedover amount and with expiring days only for the first level
        """
        accrual_plan = self.accrual_plan_2_levels_biyearly_start_limited_expiring
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 0,
        })
        allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            ('2024-01-01', 10, date(2024, 4, 1)),
        ))

        # 4 days leave
        self._create_leave(self.employee_emp, self.work_entry_type, '2024-01-02', '2024-01-07', validate=True)
        self._assert_get_allocation_data_future(allocation, (
            # Carryover date, 4 days of leave -> 6 remaining days, only 5 days are carriedover, number of days = remaining + leaves taken
            ('2024-04-01', 9, 5),
        ))

        self._assert_get_allocation_data(allocation, (
                # Assert data are the same after running the cron
                ('2024-04-01', 9, date(2024, 7, 1), 9, 5),
            ), ('number_of_days', 'nextcall', 'allocated_duration', 'remaining_leaves'))

        # 2x1 day leave
        self._create_leave(self.employee_emp, self.work_entry_type, '2024-04-02', '2024-04-02', validate=True)
        self._create_leave(self.employee_emp, self.work_entry_type, '2024-10-01', '2024-10-01', validate=True)

        year_2024_half_days = self._get_period_days('2024-07-01', '2024-12-31')
        year_2024_added_duration_1 = self._get_period_days('2024-07-01', '2024-08-31') / year_2024_half_days * 10
        year_2024_added_duration_2 = self._get_period_days('2024-09-01', '2024-12-31') / year_2024_half_days * 15
        self._assert_get_allocation_data_future(allocation, (
            # TBFIR: 'left' should be set to '3 + year_2024_added_duration_1'
            ('2024-07-01', days := 9 + year_2024_added_duration_1, left := 3 + year_2024_added_duration_1 + 1),
            # Level transition accrual + days of the first level expires (- 5 + 2 because 2 days were taken in the meantime)
            ('2024-11-01', days := days + year_2024_added_duration_2 - 3, left := 3 + year_2024_added_duration_1 + year_2024_added_duration_2 - 3),
            # Second accrual of the second level
            ('2025-01-01', days := days + 15, left + 15),
            # Carryover date: only 10 days are carriedover
            ('2025-04-01', min(days, 10) + 6, 10),
        ))
        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Second accrual of the first level
            ('2024-07-01', days := 9 + year_2024_added_duration_1, date(2024, 9, 1)),
            # Level transition
            ('2024-09-01', days := days + year_2024_added_duration_2, date(2024, 11, 1)),
            # Days of the first level are expiring + the 2 leaves taken in the meantime
            ('2024-11-01', days := days - 5 + 2, date(2025, 1, 1)),
            # Expiration date of the first level + accrual for the first period of the year with the second level
            ('2025-01-01', days := days + 15, date(2025, 4, 1)),
            # Carryover date, 10 days are carriedover
            ('2025-04-01', days := min(days, 10) + 6, date(2025, 7, 1)),
            # Second accrual of the second level
            ('2025-07-01', days := days + 15, date(2026, 1, 1)),
        ))

    def test_time_off_balance_computation(self):
        """ Assert `get_allocation_data` computes properly the balance of a time off type
            which is linked to an accrual allocation with expiring days + limited amount
            of carriedover duration
        """
        accrual_plan = self.accrual_plan_yearly_carryover_limited_expiring
        with freeze_time('2023-01-01'):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.work_entry_type.id,
                'number_of_days': 0,
            })
            allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # Accrual for the first period
                ('2024-01-01', 10, date(2024, 4, 1), 10, 10),
                ('2024-01-01', lambda:
                    self._create_leave(self.employee_emp, self.work_entry_type, '2024-03-25', '2024-03-26', validate=True)),
                # Carryover happens: only five days are kept
                ('2024-04-01', 7, date(2024, 9, 1), 7, 5),
                ('2024-04-01', lambda:
                    self._create_leave(self.employee_emp, self.work_entry_type, '2024-04-02', '2024-04-02', validate=True)),
                # Expiring date: there are 4 left days, 5 are expiring
                # Number of days is set to the number of leaves (3d) + the left days (0)
                ('2024-09-01', 3, date(2025, 1, 1), 3, 0),
                # Accrual for the year 2024
                ('2025-01-01', 13, date(2025, 4, 1), 13, 10),
                ('2025-01-01', lambda:
                    self._create_leave(self.employee_emp, self.work_entry_type, '2025-01-08', '2025-01-10', validate=True)),
                # Carryover date: 5 days are carriedover
                # Number of days = 6 days of leave + the left days (5)
                ('2025-04-01', 11, date(2025, 9, 1), 11, 5),
            ),
            ('number_of_days', 'nextcall', 'allocated_duration', 'remaining_leaves'),
        )

    @freeze_time('2024-09-02')
    def test_start_accrual_gain_time_immediately(self):
        """ Very simple test for an accrual allocation which accrues monthly at the start of the period
            while taking a leave
        """
        accrual_plan = self.accrual_plan_monthly_start_carryover_year_start
        accrual_plan.level_ids[0].write({
            'added_value': 1.25,
            'first_day': 1,
        })

        allocation = self._create_form_test_accrual_allocation(self.work_entry_type, '2024-09-02', self.employee_emp, accrual_plan)
        allocation.action_approve()

        create_leave_command = self._build_create_leave_command(self.employee_emp, self.work_entry_type)
        first_period_days = self._get_period_days('2024-09-02', '2024-09-30')
        first_accrual_month_days = self._get_period_days('2024-09-01', '2024-09-30')
        self._assert_get_allocation_data(allocation, (
                # Accrual for the first period
                ('2024-09-02', days := first_period_days / first_accrual_month_days * 1.25, date(2024, 10, 1), days, days),
                # Taking a 1 day leave
                ('2024-09-02', create_leave_command('2024-09-13 08:00:00', '2024-09-13 17:00:00')),
                # Assert nothing changed as the taken leave is in the future
                ('2024-09-02', days, date(2024, 10, 1), days, days),
                # Assert the remaining leaves are computed accordingly (1 day less)
                ('2024-09-14', days, date(2024, 10, 1), days, days - 1),
                # Accrual keeps on going
                ('2024-10-01', days := days + 1.25, date(2024, 11, 1), days, days - 1),
            ),
            ('number_of_days', 'nextcall', 'allocated_duration', 'remaining_leaves'),
        )

    @freeze_time('2024-11-25')
    def test_accrual_days_left_under_carryover_maximum(self):
        """ Assert `get_allocation_data` correctly computes the future balance of a `work.entry.type` linked
            to an accrual allocation that accrues yearly at the start of the period, with a limited amount
            of carriedover duration
        """
        accrual_plan = self.accrual_plan_yearly_start_max_leave_carryover_limited
        allocation = self._create_form_test_accrual_allocation(self.work_entry_type, '2024-01-01', self.employee_emp,
            accrual_plan, creator_user=self.user_hrmanager)
        allocation.action_approve()

        self._assert_get_allocation_data_future(allocation, (
            ('2025-01-01', 28, 28),
            ('2026-01-01', 28, 28),
            # Take a 15 days leave
            ('2024-11-25', lambda:
                self._create_leave(self.employee_emp, self.work_entry_type, '2024-10-07', '2024-10-25', validate=True)),
            # TBFIR: should be 28 + 15 and 28
            ('2025-01-01', 27 + 15, 27),
            ('2026-01-01', 28 + 15, 28),
        ))

    @freeze_time('2024-11-25')
    def test_accrual_unused_accrual_reset_to_lost(self):
        """ Assert `get_allocation_data` correctly computes the future balance of a `work.entry.type` linked
            to an accrual allocation that accrues yearly at the start of the period, when all days are lost
            on carryover date
            Also assert creating the accrual plan only level using a form works
        """
        accrual_plan = self.accrual_plan_no_level_start_carryover_year_start

        plan = self.env["hr.leave.accrual.level"].create({
            "accrual_plan_id": accrual_plan.id,
        })

        with Form(plan) as f:
            f.added_value = 21
            f.frequency = 'yearly'
            f.yearly_day = "1"
            f.cap_accrued_time = True
            f.maximum_leave = 28
            f.start_count = 0
            # Set a maximum carry-over
            f.action_with_unused_accruals = 'all'
            f.carryover_options = 'limited'
            f.max_carriedover_duration = 7
            # Set it back to 'lost'
            f.action_with_unused_accruals = 'lost'

        allocation = self._create_form_test_accrual_allocation(self.work_entry_type, '2024-01-01', self.employee_emp,
            accrual_plan, creator_user=self.user_hrmanager)
        allocation.action_approve()

        self._assert_get_allocation_data_future(allocation, (
            ('2025-01-01', 21, 21),
            ('2026-01-01', 21, 21),
            # Take a 15 days leave
            ('2024-11-25', lambda:
                self._create_leave(self.employee_emp, self.work_entry_type, '2024-10-07', '2024-10-25', validate=True)),
            # total_allocated_duration: remaining leaves + taken leaves
            ('2025-01-01', 21 + 15, 21),
            ('2026-01-01', 21 + 15, 21),
        ))

    @freeze_time("2017-12-05")
    def test_accrual_allocation_without_working_hours(self):
        """ Assert creating an accrual allocation for an employee without
            working hours doesn't raise a traceback error
        """
        employee_without_calendar = self.employee_without_calendar
        accrual_plan = self.accrual_plan_hourly_work_time
        self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
            'name': 'accrual allocation for employee without calendar',
            'accrual_plan_id': accrual_plan.id,
            'employee_id': employee_without_calendar.id,
            'work_entry_type_id': self.work_entry_type.id,
            'number_of_days': 0,
            'date_from': '2017-12-04',
        })
        self._run_update_accrual_cron("2017-12-06")

    def test_accrual_allocation_with_virtual_future_leaves(self):
        """ Assert running the accrual CRON after taking a leave that isn't
            validated (virtual leave) doesn't raise a traceback
        """
        work_entry_type = self.work_entry_type
        accrual_plan = self.accrual_plan_yearly_carryover_lost
        accrual_plan.level_ids[0].added_value = 8

        with freeze_time("2024-12-01"):
            allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).create({
                'name': 'Accrual allocation for employee',
                'accrual_plan_id': accrual_plan.id,
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': work_entry_type.id,
                'date_from': '2024-12-01',
                'number_of_days': 8,
            })
            allocation.action_approve()
            # A virtual leave that is pending approval and will be taken after the carryover date
            leave = self._create_leave(self.employee_emp, work_entry_type, '2025-01-02', '2025-01-03', additionnal_ctx={'leave_fast_create': True})
            self.assertNotEqual(leave.state, 'validate', "The leave request should not be in the 'validate' state")

        # Run the CRON to check that no validation error appears
        with freeze_time("2025-01-05"):
            self._run_update_accrual_cron()
            # Days are lost (carryover) and then accrual for the following year happens (+8d)
            self.assertEqual(allocation.number_of_days, 8, "The number of days should be updated successfully")

    def test_accrual_allocation_constraint_1(self):
        """ Assert bimonthly frequency `first_day` and `second_day` constraint works properly
        """
        with self.assertRaisesRegex(ValidationError, 'The first day must be lower than the second day.'):
            self.env['hr.leave.accrual.plan'].create({
                'name': 'Accrual Plan with no carryover',
                'accrued_gain_time': 'start',
                'carryover_date': 'year_start',
                'level_ids': [Command.create({
                    'frequency': 'bimonthly',
                    'first_day': '20',
                    'second_day': '3',
                })],
            })

    @freeze_time('2024-01-01')
    def test_accrual_allocation_data_with_different_units(self):
        """ Assert `get_allocation_data` properly computes the balance of a time type with `request_unit = unit_of_measure = 'day'`,
            while there is an accrual allocation with `added_value_type = 'hour'`
            Also assert the time type balance is updated correctly when taking a 1 day leave
        """
        accrual_plan = self.accrual_plan_daily_hour
        work_entry_type_day = self.work_entry_type_day

        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': work_entry_type_day.id,
            'number_of_days': 0,
            'accrual_plan_id': accrual_plan.id,
            'date_from': '2024-01-01',
        })
        allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # 1 hour per day, so 8 hours should've been accrued
                ('2024-01-09', days := 8 / self.hours_per_day, date(2024, 1, 10), days, days),
                # 9 days of accrual: 9x 1 hour
                ('2024-01-10', days := 9 / self.hours_per_day, date(2024, 1, 11), days, days),
                ('2024-01-10', lambda:
                    self._create_leave(self.employee_emp, work_entry_type_day, '2024-01-05', '2024-01-05', validate=True)),
                # The leave should be deducted from the remaining leaves
                ('2024-01-10', days, date(2024, 1, 11), days, days - 1),
            ),
            ('number_of_days', 'nextcall', 'allocated_duration', 'remaining_leaves')
        )

    @freeze_time('2024-01-01')
    def test_accrual_allocation_data_with_different_units_half_day(self):
        """ Assert `get_allocation_data` properly computes the balance of a time type
            with `request_unit = 'half_day'` and `unit_of_measure = 'day'`, while there
            is an accrual allocation with `added_value_type = 'hour'`
        """
        accrual_plan = self.accrual_plan_daily_hour
        work_entry_type_day = self.work_entry_type_absence_requires_alloc_half_day_day

        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': work_entry_type_day.id,
            'number_of_days': 0,
            'accrual_plan_id': accrual_plan.id,
        })
        allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # 1 hour per day, so 8 hours should've been accrued
                ('2024-01-09', days := 8 / self.hours_per_day, date(2024, 1, 10), days, days),
            ), ('number_of_days', 'nextcall', 'allocated_duration', 'remaining_leaves'))

    def test_accrual_allocation_date_in_the_future(self):
        """ Assert `get_allocation_data` properly computes the time type balance with a 4 levels accrual allocation
            with `maximum_leave` increasing from one level to the other, and max 5 carriedover days
        """
        with freeze_time('2025-01-01'):
            accrual_plan = self.accrual_plan_4_lvls_start_max_leaves_carryover_limited_expiring
            work_entry_type = self.work_entry_type_day
            allocation = self.env['hr.leave.allocation'].create({
                'name': 'Accrual allocation for employee',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': work_entry_type.id,
                'number_of_days': 20,
                'accrual_plan_id': accrual_plan.id,
                'date_from': '2025-01-01',
            })
            allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # Accrual on 2025-01-01 -> 20 days
                # On 2026-01-01:
                # - carryover kicks in, the number of days goes from 25 to 5 (only 5 days are kept and will expire 6 months later)
                # - accrual time: the allocation is accrued 20 days
                ('2026-03-01', 25),
                # Carryover expires on 2026-06-01 -> 25 - 5 = 20
                ('2026-09-01', 20),
                # Accrual on 2027-01-01 -> min(20 + 21, 26) = 26 (maximum_leave=26)
                ('2027-03-01', 26),
                # Carryover expires on 2027-06-01 -> 26 - 5 = 21
                ('2027-09-01', 21),
                # Accrual on 2028-01-01 -> min(21 + 21, 26) = 26 (maximum_leave=26)
                ('2028-03-01', 26),
                # Carryover expires on 2028-06-01 -> 26 - 5 = 21
                ('2028-09-01', 21),
                # Accrual on 2029-01-01 -> min(21 + 22, 27) = 27 (maximum_leave=27)
                ('2029-03-01', 27),
                # Carryover expires on 2029-06-01 -> 27 - 5 = 22
                ('2029-09-01', 22),
                # Accrual on 2030-01-01 -> min(22 + 22, 27) = 27 (maximum_leave=27)
                ('2030-03-01', 27),
                # Carryover expires on 2030-06-01 -> 27 - 5 = 22
                ('2030-09-01', 22),
                # Accrual on 2031-01-01 -> min(22 + 23, 28) = 28 (maximum_leave=28)
                ('2031-03-01', 28),
                # Carryover expires on 2031-06-01 -> 28 - 5 = 23
                ('2031-09-01', 23),
            ),
            ['allocated_duration'],
        )

    def test_accrual_plan_cleared_when_switch_to_regular(self):
        """ Assert the `accrual_plan_id` of an allocation is set to False when switching back to
            a regular allocation from a form
        """
        accrual_plan = self.dummy_accrual_plan
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Accrual allocation for employee',
            'work_entry_type_id': self.work_entry_type.id,
            'accrual_plan_id': accrual_plan.id,
            'employee_id': self.employee_emp.id,
            'number_of_days': 10,
        })
        self.assertEqual(allocation.accrual_plan_id, accrual_plan, "Accrual plan should initially be set.")

        with Form(allocation) as alloc_form:
            alloc_form.accrual_plan_id = self.env['hr.leave.accrual.plan']
        self.assertFalse(
            allocation.accrual_plan_id,
            "accrual_plan_id should be cleared when set to empty.",
        )
        self.assertEqual(accrual_plan.employees_count, 0, "Accrual plan should not have any linked employees.")

    def test_accrual_plan_start_carryover_expiring_3_months(self):
        """ Assert the allocated duration and the `previous_carryover_number_of_days` for an accrual allocation with
            2 levels are properly computed when some day are expiring a few months after the carryover date
        """
        with freeze_time('2025-07-01'):
            allocation = self._create_form_test_accrual_allocation(
                self.work_entry_type_day, '2025-07-01', self.employee_emp, self.accrual_plan_start1)
            allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # 11 months  =>  12 accruals as "accrued_gain_time" is "start"  =>  12 * 1 (first level) = 12
                # previous_carryover_nbr_of_days should be 0
                ('2026-06-01', expected_nbr_of_days := 12, 0),
                # Another monthly accrual
                # Do not include the 1 accrued day for 2026-07-01 for the previous_carryover_nbr_of_days
                # (otherwise it would be like wasting the days the employee earned trough the last month)
                ('2026-07-01', expected_nbr_of_days := expected_nbr_of_days + 1, 12),
                # The day before 12 days should expire + level transition -> 2 more second level monthly (2 + 2)
                ('2026-09-30', expected_nbr_of_days := expected_nbr_of_days + 4, 12),
                # Carryover expires + new monthly accrual
                ('2026-10-01', expected_nbr_of_days := expected_nbr_of_days - 12 + 2, 12),
                # Accrual keeps going
                ('2026-11-01', expected_nbr_of_days + 2, 12),
            ),
            ('allocated_duration', 'previous_carryover_number_of_days'),
        )

    def test_accrual_plan_end_carryover_expiring_3_months(self):
        """ Same test than `test_accrual_plan_start_carryover_expiring_3_months`, but for an
            accrual plan that grants days at the end of the month.
        """
        with freeze_time('2025-07-01'):
            allocation = self._create_form_test_accrual_allocation(
                self.work_entry_type_day, '2025-07-01', self.employee_emp, self.accrual_plan_end1)
            allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # 11 months  =>  11 accruals as "accrued_gain_time" is "end"  =>  11 * 1 (first level) = 11
                ('2026-06-01', expected_nbr_of_days := 11, 0),
                # Another monthly accrual
                # Do not include the 1 accrued day for 2026-07-01 for the expiring days
                # (otherwise it would be like wasting the days the employee earned trough the last month)
                ('2026-07-01', expected_nbr_of_days := expected_nbr_of_days + 1, 11),
                # The day before 12 days should expire + level transition -> 1 accrual from first level,
                # and another one from the second level (1 + 2)
                ('2026-09-30', expected_nbr_of_days := expected_nbr_of_days + 3, 11),
                # Carryover expires + new monthly accrual
                ('2026-10-01', expected_nbr_of_days := expected_nbr_of_days - 11 + 2, 11),
                # Accrual keeps going
                ('2026-11-01', expected_nbr_of_days + 2, 11),
            ), ('allocated_duration', 'previous_carryover_number_of_days'),
        )

    @freeze_time("2026-01-26")
    def test_get_additionnal_future_leaves_on(self):
        """ Assert accrual plan allocation `_get_additionnal_future_leaves_on` uses the
            `unit_of_measure` and not the `request_unit` of the leave type
        """
        allocation_day = self.env['hr.leave.allocation'].create({
            'name': 'Daily Accrual',
            'work_entry_type_id': self.work_entry_type_day.id,
            'employee_id': self.employee_emp.id,
            'accrual_plan_id': self.accrual_plan_start1.id,
            'number_of_days': 0,
            'date_from': "2026-01-26",
        })

        allocation_day._action_validate()

        # First period accrual: 2026-01-26 -> 2026-02-01
        # Second period accrual: 2026-02-01 -> 2026-03-01: +1 day
        # _get_additionnal_future_leaves_on round at 2 digits
        res_day = allocation_day._get_additionnal_future_leaves_on(date(2026, 2, 15))
        first_period_accrued_days = self._get_period_days('2026-01-26', '2026-01-31') / self._get_period_days('2026-01-01', '2026-01-31')
        self.assertAlmostEqual(res_day, 1 + first_period_accrued_days, delta=0.01)

        # Assuming an 8-hour workday, 2 days = 16.0 hours
        accrual_plan = self.accrual_plan_monthly_start
        self.employee_emp.resource_calendar_id = self.calendar_8h_per_day
        work_entry_type_hour = self.work_entry_type_hour_day
        allocation_hour = self.env['hr.leave.allocation'].create({
            'name': 'Hourly Allocation with daily accrual',
            'work_entry_type_id': work_entry_type_hour.id,
            'employee_id': self.employee_emp.id,
            'accrual_plan_id': accrual_plan.id,
            'number_of_days': 0,
            'date_from': '2026-01-01',
        })
        allocation_hour._action_validate()

        # 2026-01-01 -> 2026-02-01: +2 days
        # 2026-02-01 -> 2026-03-01: +2 days
        # -> 4 days = 32 hours accordingly to the calendar of the employee
        res_hour = allocation_hour._get_additionnal_future_leaves_on(date(2026, 2, 2))
        self.assertEqual(res_hour, 32.0)

    def test_accrual_allocation_immediate_monthly_start_day(self):
        """ Assert modifying the `date_from` from the form of an accrual allocation updates the `number_of_days` accordingly
            and that carriedover duration expires properly
        """
        with freeze_time('2024-11-15'):
            accrual_plan = self.accrual_plan_monthly_start_carryover_limited_expiring

            with Form(self.env['hr.leave.allocation'], 'hr_holidays.hr_leave_allocation_view_form_manager') as form:
                form.name = 'Test accrual allocation'
                form.accrual_plan_id = accrual_plan
                form.employee_id = self.employee_emp
                form.work_entry_type_id = self.work_entry_type

                # Accrual for November
                form.date_from = '2024-11-01'
                self.assertEqual(form.number_of_days_display, 2)

                # 2 months elapsed = 2 x 2 days
                form.date_from = '2024-10-01'
                self.assertEqual(form.number_of_days_display, 4)

                # 4 months elapsed, but only 5 days are kept on carryover date (1st of Nov.)
                # + accrual for November
                form.date_from = '2024-08-01'
                self.assertEqual(form.number_of_days_display, 7)

                # Repeat and see what happens
                form.date_from = '2024-10-01'
                self.assertEqual(form.number_of_days_display, 4)

                form.date_from = '2024-08-01'
                self.assertEqual(form.number_of_days_display, 7)

            allocation = form.record
            self.assertEqual(allocation.number_of_days_display, 7)
            allocation.action_approve()

        with freeze_time('2024-12-01'):
            self._run_update_accrual_cron()
            # Expiration date: 5 days are expiring, then 2 days are accrued for December
            self.assertEqual(allocation.number_of_days, 7 - 5 + 2)

    def test_modify_cap_accrued_days(self):
        """ Assert the virtual remaining leaves of the employee drop to `maximum_leave` when setting
            `cap_accrued_time` of the accrual plan to `True` and the virtual remaining leaves was
            bigger than `maximum_leave`
        """
        with freeze_time('2021-01-01'):
            accrual_plan = self.accrual_plan_monthly_end
            work_entry_type_day = self.work_entry_type_day
            allocation = self._create_form_test_accrual_allocation(work_entry_type_day, '2021-01-01', self.employee_emp, accrual_plan)
            allocation.action_approve()

        with freeze_time('2022-01-01'):
            self._run_update_accrual_cron()
            # 12 months accrual x 2 days
            self._assert_allocation_balance(allocation, 24, 24)
            # One more month accrual
            self._assert_allocation_balance(allocation, 26, 26, '2022-02-01')

            accrual_plan.level_ids.update({'maximum_leave': 21, 'cap_accrued_time': True})
            # Now the number_of_days and remaining leaves are capped to 21
            self._assert_allocation_balance(allocation, 21, 21, '2022-02-01')

        with freeze_time('2022-02-01'):
            # Assert we get the same balance when running the cron
            self._run_update_accrual_cron()
            self._assert_allocation_balance(allocation, 21, 21)

    def test_modify_cap_accrued_days_with_leaves(self):
        """ Assert the virtual remaining leaves of the employee drop to `maximum_leave` when setting `cap_accrued_time` of the accrual plan
            to `True` and the virtual remaining leaves was bigger than `maximum_leave`
            Adds leaves in the computation (only difference with `test_modify_cap_accrued_days`)
        """
        with freeze_time('2020-01-01'):
            accrual_plan = self.accrual_plan_monthly_end
            work_entry_type_day = self.work_entry_type_day
            allocation = self._create_form_test_accrual_allocation(work_entry_type_day, '2020-01-01', self.employee_emp, accrual_plan)
            allocation.action_approve()

        with freeze_time('2022-01-01'):
            self._run_update_accrual_cron()
            # 24 * 2 accrued days
            self._assert_allocation_balance(allocation, 48, 48)
            # 35 days leave
            self._create_leave(self.employee_emp, work_entry_type_day, '2022-01-03', '2022-02-18', validate=True)
            # 10 days leave
            self._create_leave(self.employee_emp, work_entry_type_day, '2022-03-07', '2022-03-18', validate=True)

        with freeze_time('2022-03-01'):
            self._run_update_accrual_cron()
            self._assert_get_allocation_data_future(allocation, (
                # number_of_days: 48 + 2 months accrual
                # remaining duration after the first leave: 48 - 35 + 4
                ('2022-03-01', 52, 17),
                ('2022-03-01', lambda:
                    accrual_plan.level_ids.update({'maximum_leave': 21, 'cap_accrued_time': True})),
                # Cap isn't reached, is changes nothing
                ('2022-03-01', 52, 17),
                # The second leave is taken into account (-10d), +2 days accrued for April
                ('2022-04-01', 54, 9),
            ))

        with freeze_time('2022-04-01'):
            self._run_update_accrual_cron()
            self._assert_get_allocation_data_future(allocation, (
                ('2022-04-01', 54, 9),
                # The max number of leaves is reached one year later so the number_of_days is 45 (leaves) + 21 (max),
                # and the remaining number of days is 21
                ('2023-03-01', 66, 21),
            ))

        with freeze_time('2023-03-01'):
            self._run_update_accrual_cron()
            # Assert the cap is still applied after running the cron
            self._assert_allocation_balance(allocation, 66, 21, '2023-03-01')

    def test_get_allocation_actual_future_leaves(self):
        """ Assert `get_allocation_data` properly computes the balance of a `work.entry.type`
            which is linked to an accrual allocation that has max 10 available leaves while
            taking multiple leaves (the balance used to be frozen after the first leave)
        """
        with freeze_time('2019-01-01'):
            accrual_plan = self.accrual_plan_monthly_end_max_leaves
            work_entry_type_day = self.work_entry_type_day
            allocation = self._create_form_test_accrual_allocation(work_entry_type_day, '2019-01-01', self.employee_emp, accrual_plan)
            allocation.action_approve()

        create_leave_command = self._build_create_leave_command(self.employee_emp, work_entry_type_day)
        self._assert_get_allocation_data(allocation, (
                ('2022-01-01', 10, 10, 10),
                # 10 days leave
                ('2022-01-01', create_leave_command('2022-01-03', '2022-01-14')),
                # 10 days leave
                ('2022-01-01', create_leave_command('2023-01-02', '2023-01-13')),
                # 10 days leaves that shouldn't be taken into account in this test
                ('2022-01-01', create_leave_command('2025-10-06', '2025-10-17')),
                # The first leave is taken into account + accrual for January
                ('2022-02-01', 12, 12, 2),
                # The cap is reache again
                ('2023-01-01', 20, 20, 10),
                # The first and second leaves are taken into account, + accrual for January
                ('2023-02-01', 22, 22, 2),
            ),
            ('number_of_days', 'allocated_duration', 'remaining_leaves'),
        )

    def test_get_allocation_future_leaves(self):
        """ Assert the virtual remaining leaves of the employee allocation are not frozen while taking multiple leaves
            and using `get_allocation_data` with the `target_date` parameter set in the future.
        """
        with freeze_time('2019-01-01'):
            accrual_plan = self.accrual_plan_monthly_end_max_leaves
            work_entry_type_day = self.work_entry_type_day
            allocation = self._create_form_test_accrual_allocation(work_entry_type_day, '2019-01-01', self.employee_emp, accrual_plan)
            allocation.action_approve()

        create_leave_command = self._build_create_leave_command(self.employee_emp, work_entry_type_day)

        with freeze_time('2022-01-01'):
            self._run_update_accrual_cron()
            self._assert_get_allocation_data_future(allocation, (
                # Max number of leaves for the only level of the accrual plan is 10
                ('2022-01-01', 10, 10),
                ('2022-02-01', 10, 10),
                # 10 days leave
                ('2022-01-01', create_leave_command('2022-01-03', '2022-01-14')),
                # 10 days leave
                ('2022-01-01', create_leave_command('2023-01-02', '2023-01-13')),
                # 10 days leaves that shouldn't be taken into account in this test
                ('2022-01-01', create_leave_command('2025-10-06', '2025-10-17')),
                # Right after spending all the 10 leaves ('2023-01-02' -> '2023-01-13')
                # 20 days - 2x10 days (leaves) + 2 days (1 month accrual)
                ('2023-02-01', 22, 2),
            ))

    def _test_get_allocation_future_leaves_regular(self, regular_before):
        """ Assert `_get_allocation_data` computes properly the future `work.entry.type` balance while taking multiple leaves
            :param regular_before: set the `date_from` of the regular allocation before the `date_from` of the accrual allocation
        """
        work_entry_type_day = self.work_entry_type_day
        if regular_before:
            with freeze_time('2018-01-01'):
                self._create_form_test_regular_allocation(work_entry_type_day, '2018-01-01', self.employee_emp, 10)

        with freeze_time('2019-01-01'):
            accrual_plan = self.accrual_plan_monthly_end_max_leaves
            accrual_allocation = self._create_form_test_accrual_allocation(work_entry_type_day, '2019-01-01', self.employee_emp, accrual_plan)
            accrual_allocation.action_approve()

        if not regular_before:
            with freeze_time('2020-01-01'):
                self._create_form_test_regular_allocation(work_entry_type_day, '2020-01-01', self.employee_emp, 10)

        create_leave_command = self._build_create_leave_command(self.employee_emp, work_entry_type_day)
        with freeze_time('2022-01-01'):
            self._run_update_accrual_cron()
            self._assert_get_allocation_data(accrual_allocation, (
                # Accrual allocatin maximum is reached (10d) + 10d for the regular allocation
                ('2022-01-01', 20, 20),
                ('2022-02-01', 20, 20),
                # 2x10 days leave
                ('2022-01-01', create_leave_command('2022-01-03', '2022-01-14')),
                ('2022-01-01', create_leave_command('2023-01-02', '2023-01-13')),
                # Assert nothing changed ('cause the leaves are in the future)
                ('2022-01-01', 20, 20),
                # The 2 leaves should be covered by the the accrual allocation => 10 days left (regular allocation) + 2 days accrual
                # Until '2023-01-01', the 'number_of_days' should be stuck to 30:
                # - 10 days regular alloc
                # - 20 days accrual alloc (max 10 leaves, but 10 leaves were taken)
                ('2023-01-01', 30, 20),
                ('2023-02-01', 32, 12),
                # 10 days leaves that shouldn't be taken into account in this test
                ('2022-01-01', create_leave_command('2023-10-06', '2023-10-17')),
                ('2023-02-01', 32, 12),
            ),
            ('allocated_duration', 'remaining_leaves'),
        )

    def test_get_allocation_future_leaves_regular1(self):
        self._test_get_allocation_future_leaves_regular(regular_before=False)

    def test_get_allocation_future_leaves_regular2(self):
        self._test_get_allocation_future_leaves_regular(regular_before=True)

    def test_work_entry_unit_of_measure_hour(self):
        """ Assert remaining leaves and number of days granted by an accrual plan allocation are correct when using a
            `work.entry.type` with `unit_of_measure` set to 'hour' and `request_unit` set to 'day', knowing that
            all days are lost on carryover day
        """
        work_entry_type = self.work_entry_type_hour_day
        with freeze_time('2025-01-01'):
            allocation = self._create_form_test_accrual_allocation(
                work_entry_type, '2025-01-01', self.employee_emp, self.accrual_plan_monthly_start_carryover_lost)
            self.assertEqual(allocation.number_of_days, 1)
            allocation.action_approve()
            # 2x1 day leave
            self._create_leave(self.employee_emp, work_entry_type, '2025-01-03', '2025-01-03', validate=True)
            self._create_leave(self.employee_emp, work_entry_type, '2025-02-03', '2025-02-03', validate=True)

        self._assert_get_allocation_data(allocation, (
                # No more remaining leave once on the first leave first day
                ('2025-01-03', 8, 0),
                ('2025-02-01', 16, 8),
                # No more remaining leave once on the second leave first day
                ('2025-02-03', 16, 0),
                # Monthly accrual keeps going
                ('2025-03-01', 24, 8),
                ('2025-04-01', 32, 16),
                # Carryover happens and removes the 2 remaining days, then monthly accrual happens (+1d)
                ('2025-05-01', 24, 8),
                ('2025-06-01', 32, 16),
                ('2025-07-01', 40, 24),
            ),
            ('allocated_duration', 'remaining_leaves'),
        )

    def test_work_entry_unit_of_measure_day(self):
        """ Assert the `work.entry.type` balance is correct when linked to an accrual allocation while using a
            `work.entry.type` with `unit_of_measure` set to 'hour' and `request_unit` set to 'day', knowing that
            all days are lost on carryover day
        """
        work_entry_type = self.work_entry_type_day_hour
        with freeze_time('2025-01-01'):
            allocation = self._create_form_test_accrual_allocation(
                work_entry_type, '2025-01-01', self.employee_emp, self.accrual_plan_monthly_start_carryover_lost_hour)
            allocation.action_approve()
            # 2x1 day leave
            self._create_leave(self.employee_emp, work_entry_type, '2025-01-03', '2025-01-03', validate=True)
            self._create_leave(self.employee_emp, work_entry_type, '2025-02-03', '2025-02-03', validate=True)

        # As 'unit_of_measure = day', get_allocation_data will return remaining and allocated duration in day
        self._assert_get_allocation_data(allocation, (
                # Accrual for the first month
                ('2025-01-01', 1, 1),
                # First leave is taken into account, remaining leave decreases of 1 day
                ('2025-01-03', 1, 0),
                # Accrual for the second month
                ('2025-02-01', 2, 1),
                # Second leave happens, remaining leave decreases of 1 day
                ('2025-02-03', 2, 0),
                # Third accrual
                ('2025-03-01', 3, 1),
                ('2025-04-01', 4, 2),
                # Carryover happens, days are lost + accrual for May
                ('2025-05-01', 3, 1),
                # Accruals keep on going...
                ('2025-06-01', 4, 2),
                ('2025-07-01', 5, 3),
            ),
            ('allocated_duration', 'remaining_leaves'),
        )

    @freeze_time('2024-11-25')
    def test_accrual_days_left_over_carryover_maximum_with_leaves_around_carryover(self):
        """ Assert `get_allocation_data` properly compute the work entry type balance when it is linked to
            an accrual allocation while taking some leaves (the remaining leaves used to be frozen)
        """
        allocation = self._create_form_test_accrual_allocation(
            self.work_entry_type_day, '2024-01-01', self.employee_emp, self.accrual_plan_yearly_max_carriedover_days_start)
        allocation.action_approve()

        # take 10 days in the past
        self._create_leave(self.employee_emp, self.work_entry_type_day, '2024-12-09', '2024-12-20', validate=True)
        # take 10 days in January
        self._create_leave(self.employee_emp, self.work_entry_type_day, '2025-01-06', '2025-01-17', validate=True)

        # The remaining leaves on a specific date should be:
        # 25/11/2024 to 08/12/2024: 21 days, no leave are deducted
        # 09/12/2024 to 31/12/2024: 11 days, the first leave is deducted as its start date is past
        # 01/01/2025 to 05/01/2025: 26 days, carryover occurred, from the 11 days only 5 are left, then the yearly 21 days are added
        # from 06/01/2025: 16 days, the second leave is deducted as its start date is past
        self._assert_get_allocation_data(allocation, (
                # Accrual for the year 2024
                ('2024-01-01', 21.0, 21.0),
                ('2024-12-01', 21.0, 21.0),
                # First leave is taken into account
                ('2024-12-15', 21.0, 11.0),
                # 5 days are carriedover, then the accrual for the year 2025 happens
                ('2025-01-01', 36.0, 26.0),
                # Second leave is taken into account
                ('2025-01-06', 36.0, 16.0),
            ),
            ('allocated_duration', 'remaining_leaves'),
        )

    @freeze_time("2024-01-01")
    def test_accrual_leaves_cancel_cron_with_refused_allocation(self):
        """ Test that the `_cancel_invalid_leaves` cron cancels a leave that is linked to a work entry
            type having only a refused accrual allocation
        """
        work_entry_type = self.work_entry_type_absence_requires_alloc_negativ
        accrual_plan = self.dummy_accrual_plan
        allocation = self.env['hr.leave.allocation'].create({
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': work_entry_type.id,
            'accrual_plan_id': accrual_plan.id,
            'number_of_days': 1,
        })

        leave = self._create_leave(self.employee_emp, work_entry_type, '2024-01-05', '2024-01-05')

        allocation.action_refuse()
        self.env['hr.leave']._cancel_invalid_leaves()
        self.assertEqual(leave.state, 'cancel')

    @freeze_time('2026-01-01')
    def test_department_accrual_allocation(self):
        """ Assert that `number_of_days` is computed properly on the allocation generated through
            a multi employee accrual allocation
        """
        employees = self.dummy_test_employee | self.employee_emp
        multi_employee_allocation = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Multi-Allocation',
            'employee_ids': [Command.link(employee.id) for employee in employees],
            'work_entry_type_id': self.work_entry_type_day.id,
            'date_from': '2026-01-01',
            'accrual_plan_id': self.accrual_plan_yearly_max_carriedover_days_start.id,
        })

        multi_employee_allocation.action_generate_allocations()

        children_allocations = self.env['hr.leave.allocation'].search(
            [('employee_id', 'in', employees.ids)])
        self.assertEqual(len(children_allocations), 2)
        self.assertEqual(children_allocations[0].number_of_days, 21.0)
        self.assertEqual(children_allocations[1].number_of_days, 21.0)

    @freeze_time('2026-03-15')
    def test_multi_allocation_wizard_initializes_accrual(self):
        """ Assert that the multi-employee wizard generate one allocation when used for one employee
            Also assert the `number_of_days` of this allocation is updated properly
        """
        wizard = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Compute Accruals',
            'employee_ids': [Command.link(self.employee_emp.id)],
            'work_entry_type_id': self.work_entry_type.id,
            'accrual_plan_id': self.accrual_plan_daily_end.id,
            'date_from': '2026-03-01',
            'duration': 0.0,
        })
        wizard.action_generate_allocations()

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', [self.employee_emp.id]),
            ('accrual_plan_id', '=', self.accrual_plan_daily_end.id),
            ('date_from', '=', datetime.date(2026, 3, 1)),
        ])
        self.assertEqual(len(allocations), 1, "Should create one allocation for the employee.")
        self.assertEqual(allocations.number_of_days, 14.0, "Should compute 14 days of accrual for the employee (from March 1st to March 15th).")

    @freeze_time('2026-03-15')
    def test_multi_allocation_wizard_does_not_recompute_when_duration_is_set(self):
        """ Assert setting the `duration` of the accrual allocation when using the multi-employee wizard
            sets the number_of_days of the generated accrual allocation, and that it is not recomputed if
            the cron is run on the same day
        """
        wizard = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Keep Manual Setting',
            'employee_ids': [(4, self.employee_emp.id)],
            'work_entry_type_id': self.work_entry_type.id,
            'accrual_plan_id': self.accrual_plan_monthly_end.id,
            'date_from': '2026-03-01',
            'duration': 3.0,
        })
        wizard.action_generate_allocations()

        allocation = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee_emp.id),
            ('accrual_plan_id', '=', self.accrual_plan_monthly_end.id),
            ('date_from', '=', datetime.date(2026, 3, 1)),
        ], limit=1)
        self.assertEqual(allocation.number_of_days, 3.0, "The number_of_days should've been set to the duration defined in the wizard")

        self._run_update_accrual_cron()
        # Assert nothing changes (accrual happens at the end of the month)
        self.assertEqual(allocation.number_of_days, 3.0, "The number of days should not be recomputed when duration is set.")

    def test_carryover_no_extra_accrual_start(self):
        """ Assert that no accrual happens on carryover date while using an accrual allocation which accrues
            monthly at the 15th of the month and which carryover happens at the start of the year
        """
        with freeze_time('2025-12-01'):
            accrual_plan = self.accrual_plan_monthly_start_carryover_year_start
            allocation = self._create_form_test_accrual_allocation(self.work_entry_type_day, '2025-12-01', self.employee_emp, accrual_plan)
            allocation.action_approve()

        first_period_days = self._get_period_days('2025-12-01', '2025-12-14')
        first_period_total_days = self._get_period_days('2025-11-15', '2025-12-14')
        self._assert_get_allocation_data(allocation, (
                # Accrual for 2025-12-01 -> 2025-12-14 (partial period) and 2025-12-15 -> 2026-01-14
                ('2025-12-15', days := first_period_days / first_period_total_days * 2 + 2),
                # 2026-01-01: carryover date, nothing happens
                ('2026-01-01', days),
                # 2026-01-15: monthly accrual keeps going
                ('2026-01-15', days + 2),
            ),
            ('allocated_duration',),
        )

    def test_carryover_no_extra_accrual_end(self):
        """ Assert that no accrual happens on carryover date
            Using a one level accrual plan which :
            - Adds 2 days at the end of every month on the 15th of the month
            - Has carryover at the start of the year
        """
        with freeze_time('2025-12-01'):
            accrual_plan = self.accrual_plan_monthly_end_carryover_year_start
            allocation = self._create_form_test_accrual_allocation(self.work_entry_type_day, '2025-12-01', self.employee_emp, accrual_plan)
            allocation.action_approve()

        first_period_days = self._get_period_days('2025-12-01', '2025-12-14')
        first_period_total_days = self._get_period_days('2025-11-15', '2025-12-14')
        self._assert_get_allocation_data(allocation, (
                ('2025-12-01', 0),
                # 2025-12-01 -> 2025-12-14 : 14 days
                ('2025-12-15', duration := first_period_days / first_period_total_days * 2),
                # 2026-01-01: carryover date, nothing happens
                ('2026-01-01', duration),
                # 2026-01-15: monthly accrual keeps going
                ('2026-01-15', duration + 2),
            ),
            ('allocated_duration',),
        )

    def test_carryover_no_extra_accrual_end_multi_level(self):
        """ Assert that no accrual happens on carryover date when the carryover is the last event before the carryover date
            Using a two levels accrual plan which :
            - Adds 2 days at the end of every month on the 15th of the month
            - Has carryover at the start of the year
            - Has a second level that adds 3 days on the 15th of the month and starting after 11 months
        """
        with freeze_time('2025-12-16'):
            accrual_plan = self.accrual_plan_monthly_end_carryover_year_start_2_lvls
            allocation = self._create_form_test_accrual_allocation(self.work_entry_type_day, '2025-12-16', self.employee_emp, accrual_plan)
            allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # Beginning of the accrual: 0 days
                ('2025-12-16', duration := 0),
                # Carryover date, nothing happens
                ('2026-01-01', duration),
                # Monthly accrual keeps going 2025-12-16 -> 2026-01-15 : 30 / 31
                ('2026-01-15', duration := 30 / 31 * 2),
                # Last accrual before level transition
                ('2026-12-15', duration := duration + 11 * 2),
                # Level transition: accrual happens: 2026-12-15 -> 2026-12-16 : 1 / 31
                ('2026-12-16', duration := duration + 1 / 31 * 2),
                # Carryover: nothing happens
                ('2027-01-01', duration),
                # Monthly accrual keeps going for the second level: 2026-12-16 -> 2027-01-15: 30 / 31
                ('2027-01-15', duration := duration + 30 / 31 * 3),
            ),
            ('allocated_duration',),
        )

    def test_carryover_no_extra_accrual_start_multi_level(self):
        """ Assert that no accrual happens on carryover date when the carryover is the last event before the carryover date
            Using a two levels accrual plan which :
            - Adds 2 days at the start of every month on the 15th of the month
            - Has carryover at the start of the year
            - Has a second level that adds 3 days on the 15th of the month and starting after 11 months
        """
        with freeze_time('2025-12-16'):
            accrual_plan = self.accrual_plan_monthly_start_carryover_year_start_2_lvls
            allocation = self._create_form_test_accrual_allocation(self.work_entry_type_day, '2025-12-16', self.employee_emp, accrual_plan)
            allocation.action_approve()

        self._assert_get_allocation_data(allocation, (
                # Beginning of the accrual: 2025-12-16 -> 2026-01-15: 30 / 31
                ('2025-12-16', duration := 30 / 31 * 2),
                # Carryover date, nothing happens
                ('2026-01-01', duration),
                # Monthly accrual keeps going
                ('2026-01-15', duration := duration + 2),
                # Last accrual before level transition: 10 month accrual + 2026-12-15 -> 2026-12-16 = 1 / 31
                ('2026-12-15', duration := duration + 10 * 2 + 1 / 31 * 2),
                # Level transition: accrual happens: adding the 30 days left
                ('2026-12-16', duration := duration + 30 / 31 * 3),
                # Carryover: nothing happens
                ('2027-01-01', duration),
                # Monthly accrual keeps going for the second level
                ('2027-01-15', duration := duration + 3),
            ),
            ('allocated_duration',),
        )

    def test_transition_mode_accrual_plan_end(self):
        """ When transition mode of an accrual plan is set to `end_of_accrual` and that it accrues the days at
            the end of the period, assert the previous level is used when we are past the level transition, but
            we are still in the previous level last period

            Here the accrual plan first level accrues 1 day monthly
            Second level start after 1 month and accrues 2 days monthly
        """
        with freeze_time('2026-01-15'):
            allocation = self._create_form_test_accrual_allocation(
                self.work_entry_type_day, '2026-01-15', self.employee_emp, self.accrual_plan2)
            allocation.action_approve()

        self._assert_accrual_allocation_nbr_of_days_and_nextcall(allocation, (
            # Accrual plan accrued time is 'end', so 0 days at the start
            ('2026-01-15', number_of_days := 0, date(2026, 2, 1)),
            # Accrual from 15 to 31 of January
            ('2026-02-01', number_of_days := number_of_days + (31 - 15 + 1) / 31, date(2026, 3, 1)),
            # Transition mode is set to 'end_of_accrual', nothing happens here
            ('2026-02-15', number_of_days, date(2026, 3, 1)),
            # We are past the first level, but the first level should still be used for this accrual
            ('2026-03-01', number_of_days := number_of_days + 1, date(2026, 4, 1)),
            # Second level is used for this accrual
            ('2026-04-01', number_of_days := number_of_days + 2, date(2026, 5, 1)),
        ))
