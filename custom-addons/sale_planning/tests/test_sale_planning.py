# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

import pytz

from math import ceil
from datetime import datetime, timedelta
from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo.tests import Form, tagged
from odoo.tools import mute_logger, float_compare

from .common import TestCommonSalePlanning

@tagged('post_install', '-at_install')
class TestSalePlanning(TestCommonSalePlanning):

    def test_planning_slot_form(self):
        slot_form = Form(self.env['planning.slot'])
        slot_form.sale_line_id = self.plannable_sol
        slot = slot_form.save()

        self.assertEqual(slot.sale_line_id, self.plannable_sol, 'Plannable services should have type \'service\'.')
        self.assertFalse(not slot.start_datetime, 'Salable slot created from gantt have default date')
        self.assertFalse(not slot.end_datetime, 'Salable slot created from gantt have default date')

    def test_planning_slot_not_salable(self):
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['planning.slot'].create({
                'start_datetime': False,
                'end_datetime': False,
            })

    def test_planning_sol_confirmation(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.planning_partner
        with so_form.order_line.new() as sol_form:
            sol_form.product_id = self.plannable_product
            sol_form.product_uom_qty = 50
        so = so_form.save()
        self.assertEqual(so.planning_hours_to_plan, 0.0, 'There are no hours to plan before SO confirmation.')
        self.assertEqual(so.planning_hours_planned, 0.0, 'There are no hours planned before SO confirmation.')
        self.assertFalse(so.order_line.planning_slot_ids, 'There should not exists planning slots before SO confirmation')

        so.action_confirm()
        self.assertEqual(float_compare(so.planning_hours_to_plan, 50.0, precision_digits=2), 0, 'There should be 50.0 to plan after SO confirmation.')
        self.assertEqual(so.planning_hours_planned, 0.0, 'There are no hours planned just after SO confirmation.')
        self.assertEqual(len(so.order_line.planning_slot_ids), 1, 'There should exist exactly 1 planning slot just after SO confirmation')

        slot = so.order_line.planning_slot_ids
        self.assertFalse(slot.start_datetime, 'Slot start datetime should be unset.')
        self.assertFalse(slot.end_datetime, 'Slot end datetime should be unset.')
        self.assertFalse(slot.employee_id, 'Slot should be unassigned.')
        self.assertEqual(float_compare(slot.allocated_hours, 50.0, precision_digits=2), 0, 'Slot should have 50.0 hours "allocated"')
        self.assertEqual(float_compare(slot.allocated_percentage, 100.0, precision_digits=2), 0, 'Slot should have 100%% allocated percentage')

        for field in slot._fields.keys():
            try:
                slot[field]
            except Exception as e:
                raise AssertionError("Error raised unexpectedly while computing a field of the slot! Exception: " + e.args[0])

    def test_planning_plan_order_no_employee(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.planning_partner
        with so_form.order_line.new() as sol_form:
            sol_form.product_id = self.plannable_product
            sol_form.product_uom_qty = 50
        so = so_form.save()
        so.action_confirm()
        Slot = self.env['planning.slot'].with_context(
            default_start_datetime='2021-07-25 00:00:00',
            default_end_datetime='2021-07-31 23:59:59',
            scale='week',
            focus_date='2021-07-31 00:00:00',
            planning_gantt_active_sale_order_id=so.id,
        )
        with freeze_time('2021-07-26'):
            Slot.auto_plan_ids(view_domain=[('start_datetime', '=', '2021-07-25 00:00:00'), ('end_datetime', '=', '2021-07-31 23:59:59')])
        self.assertFalse(so.order_line.planning_slot_ids.filtered('start_datetime'), 'There should be no employee corresponding to criterias.')

    def test_planning_plan_order_default_role(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.planning_partner
        with so_form.order_line.new() as sol_form:
            sol_form.product_id = self.plannable_product
            sol_form.product_uom_qty = 50
        so = so_form.save()
        so.action_confirm()
        self.employee_wout.write({'default_planning_role_id': self.planning_role_junior.id})
        Slot = self.env['planning.slot'].with_context(
            default_start_datetime='2021-07-25 00:00:00',
            default_end_datetime='2021-07-31 23:59:59',
            scale='week',
            focus_date='2021-07-31 00:00:00',
            planning_gantt_active_sale_order_id=so.id,
        )
        with freeze_time('2021-07-26'):
            Slot.auto_plan_ids(view_domain=[('start_datetime', '=', '2021-07-25 00:00:00'), ('end_datetime', '=', '2021-07-31 23:59:59')])
        slot = so.order_line.planning_slot_ids.filtered('start_datetime')
        self.assertEqual(slot.employee_id, self.employee_wout, 'Planning should be assigned to the employee with sol\'s product role as default role')

    def test_planning_plan_order_roles(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.planning_partner
        with so_form.order_line.new() as sol_form:
            sol_form.product_id = self.plannable_product
            sol_form.product_uom_qty = 50
        so = so_form.save()
        so.action_confirm()
        self.employee_wout.write({'planning_role_ids': [(4, self.planning_role_junior.id)]})
        Slot = self.env['planning.slot'].with_context(
            default_start_datetime='2021-07-25 00:00:00',
            default_end_datetime='2021-07-31 23:59:59',
            scale='week',
            focus_date='2021-07-31 00:00:00',
            planning_gantt_active_sale_order_id=so.id,
        )
        with freeze_time('2021-07-26'):
            Slot.auto_plan_ids(view_domain=[('start_datetime', '=', '2021-07-25 00:00:00'), ('end_datetime', '=', '2021-07-31 23:59:59')])
        slot = so.order_line.planning_slot_ids.filtered('start_datetime')
        self.assertEqual(slot.employee_id, self.employee_wout, 'Planning should be assigned to the employee with one of its role equal to sol\'s product role')

    def test_planning_plan_order_previous_slot(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.planning_partner
        with so_form.order_line.new() as sol_form:
            sol_form.product_id = self.plannable_product
            sol_form.product_uom_qty = 150
        so = so_form.save()
        so.action_confirm()
        Slot = self.env['planning.slot'].with_context(
            default_start_datetime='2021-07-25 00:00:00',
            default_end_datetime='2021-07-31 23:59:59',
            scale='week',
            focus_date='2021-07-31 00:00:00',
            planning_gantt_active_sale_order_id=so.id,
        )
        self.employee_wout.write({'default_planning_role_id': self.planning_role_junior})
        with freeze_time('2021-07-26'):
            Slot.auto_plan_ids(view_domain=[('start_datetime', '=', '2021-07-25 00:00:00'), ('end_datetime', '=', '2021-07-31 23:59:59')])
        self.employee_wout.write({'default_planning_role_id': False, 'planning_role_ids': [(5, 0, 0)]})
        self.employee_joseph.write({'default_planning_role_id': self.planning_role_junior.id})
        with freeze_time('2021-07-26'):
            Slot.with_context(
                default_start_datetime='2021-08-01 00:00:00',
                default_end_datetime='2021-08-07 23:59:59'
            ).auto_plan_ids(view_domain=[('start_datetime', '=', '2021-08-01 00:00:00'), ('end_datetime', '=', '2021-08-07 23:59:59')])
        slots = so.order_line.planning_slot_ids.filtered('start_datetime')
        self.assertEqual(len(slots), 2, 'It should exists two slots')
        for slot in slots:
            self.assertEqual(slot.employee_id, self.employee_wout, 'Planning should be assigned to the employee previously assigned to the slot')

        # Ensure no one is assigned once again since employee_wout is already planned this week
        with freeze_time('2021-07-26'):
            Slot.with_context(
                default_start_datetime='2021-08-01 00:00:00',
                default_end_datetime='2021-08-07 23:59:59'
            ).auto_plan_ids(view_domain=[('start_datetime', '=', '2021-08-01 00:00:00'), ('end_datetime', '=', '2021-08-07 23:59:59')])
        slots = so.order_line.planning_slot_ids.filtered('start_datetime')
        self.assertEqual(len(slots), 2, 'It should exists two slots')
        for slot in slots:
            self.assertEqual(slot.employee_id, self.employee_wout, 'Planning should be assigned to the employee previously assigned to the slot')

    def test_planning_plan_slot(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.planning_partner
        with so_form.order_line.new() as sol_form:
            sol_form.product_id = self.plannable_product
            sol_form.product_uom_qty = 50
        so = so_form.save()
        so.action_confirm()
        slot = so.order_line.planning_slot_ids
        slot.with_context(
            default_start_datetime='2021-07-25 00:00:00',
            default_end_datetime='2021-07-31 23:59:59',
            scale='week',
            focus_date='2021-07-29 00:00:00',
            planning_gantt_active_sale_order_id=so.id,
        ).write({
            'start_datetime': '2021-07-27 06:00:00',
            'end_datetime': '2021-07-27 15:00:00',
            'resource_id': self.employee_wout.resource_id.id,
        })
        planned_slot_1 = so.order_line.planning_slot_ids.filtered('start_datetime')
        self.assertEqual(1, len(planned_slot_1), 'There should be only 1 allocated slot.')
        self.assertEqual(self.employee_wout, planned_slot_1.employee_id, 'Planning should be assigned to the employee with one of its role equal to sol\'s product role')
        self.assertEqual('2021-07-27 06:00:00', str(planned_slot_1.start_datetime), 'Planning slot should take the start datetime induced by the magnifying glass in gantt')
        self.assertEqual('2021-07-30 15:00:00', str(planned_slot_1.end_datetime), 'Planning slot should last for all the week, until friday afternoon.')
        self.assertEqual(32.0, planned_slot_1.allocated_hours, 'Planning slot should have 32 allocated hours.')

        slot = so.order_line.planning_slot_ids.filtered_domain([('start_datetime', '=', False)])
        self.assertEqual(1, len(slot), 'There should exists a slot with the remaining hours to allocate.')
        self.assertEqual(18.0, slot.allocated_hours, 'There should exists a slot with the right remaining hours to allocate.')

        slot.with_context(
            default_start_datetime='2021-08-01 00:00:00',
            default_end_datetime='2021-08-07 23:59:59',
            scale='week',
            focus_date='2021-08-02 00:00:00',
            planning_gantt_active_sale_order_id=so.id,
        ).write({
            'start_datetime': '2021-08-02 06:00:00',
            'end_datetime': '2021-08-02 15:00:00',
            'resource_id': self.employee_wout.resource_id.id,
        })

        slots = so.order_line.planning_slot_ids.filtered('start_datetime')
        for slot in slots:
            if slot != planned_slot_1:
                self.assertEqual(slot.employee_id, self.employee_wout, 'Planning should be assigned to the employee with one of its role equal to sol\'s product role')
                self.assertEqual('2021-08-02 06:00:00', str(slot.start_datetime), 'Planning slot should take the start datetime induced by the magnifying glass in gantt. (Janice has NYC Timezone)')
                self.assertEqual('2021-08-04 08:00:00', str(slot.end_datetime), 'Planning slot should last for all the week, until friday afternoon. (Janice has NYC Timezone)')
                self.assertEqual(18.0, slot.allocated_hours, 'Planning slot should have 18 allocated hours.')

    def test_copy_previous_week(self):
        self.resource_bert.default_role_id = self.planning_role_junior
        for qty, percent, hours in [(2, 40, 1), (1, 15, 2)]:
            so = self.env['sale.order'].create({
                "partner_id": self.planning_partner.id,
            })
            sol = self.env['sale.order.line'].create({
                "product_id": self.plannable_product.id,
                "product_uom_qty": qty,
                "order_id": so.id,
            })
            so.action_confirm()

            PlanningSlot = self.env['planning.slot']
            start = datetime(2019, 6, 26, 8, 0)
            PlanningSlot.create([{
                'start_datetime': start + timedelta(hours=hours * i),
                'end_datetime': start + timedelta(hours=hours * (i + 1)),
                'allocated_percentage': percent,
                'sale_line_id': sol.id,
            } for i in range(2)])

            can_create = True
            while can_create:
                start = start + timedelta(weeks=1)
                can_create = PlanningSlot.action_copy_previous_week(str(start), [
                    # dummy domain
                    ('start_datetime', '=', True),
                    ('end_datetime', '=', True),
                ])

            slots = PlanningSlot.search([
                ('sale_line_id', '=', sol.id),
                ('start_datetime', '!=', False),
            ])
            self.assertEqual(len(slots), ceil(qty / hours * 100 / percent))
            self.assertTrue(
                all(slots.mapped(lambda s: s.allocated_percentage == percent)),
                'All slots should have the same allocated percentage',
            )
            self.assertAlmostEqual(
                sum(slots.mapped(lambda s: s._get_slot_duration())) * percent / 100, qty,
                msg='Total duration * allocated percentage should be 1 hour, as sold',
            )

    def test_copy_no_allocated_percentage(self):
        """Mostly to test that the copy method does not crash when there is no allocated percentage."""
        so = self.env['sale.order'].create({
            "partner_id": self.planning_partner.id,
        })
        sol = self.env['sale.order.line'].create({
            "product_id": self.plannable_product.id,
            "product_uom_qty": 10,
            "order_id": so.id,
        })
        so.action_confirm()

        PlanningSlot = self.env['planning.slot']
        start = datetime(2019, 6, 25, 8, 0)
        slot = PlanningSlot.create({
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
            'allocated_percentage': 0,
            'sale_line_id': sol.id,
        })
        self.assertEqual(slot.allocated_percentage, 0)

        copy_start = start + timedelta(weeks=1)
        PlanningSlot.action_copy_previous_week(
            str(copy_start), [
                # dummy domain
                ('start_datetime', '=', True),
                ('end_datetime', '=', True),
            ]
        )

        copy = PlanningSlot.search([('start_datetime', '=', copy_start), ('sale_line_id', '=', sol.id)])
        self.assertEqual(len(copy), 1)
        self.assertEqual(copy.allocated_percentage, 0)
        self.assertEqual(copy.allocated_hours, 0)
        self.assertEqual(copy.end_datetime, copy_start + timedelta(hours=1))

    def test_copy_previous_week_with_slot_to_plan(self):
        so = self.env['sale.order'].create({
            'partner_id': self.planning_partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.plannable_product.id,
            'product_uom_qty': 10,
            'order_id': so.id,
        })
        so.action_confirm()

        PlanningSlot = self.env['planning.slot']
        slot_to_plan = PlanningSlot.search([('start_datetime', '=', False), ('sale_line_id', '=', sol.id)])
        self.assertEqual(len(slot_to_plan), 1)
        start = datetime(2019, 6, 25, 8, 0, tzinfo=pytz.utc)
        slot = PlanningSlot.create({
            'start_datetime': start.replace(tzinfo=None),
            'end_datetime': (start + timedelta(hours=5)).replace(tzinfo=None),
            'sale_line_id': sol.id,
        })
        self.assertEqual(slot.allocated_hours, 5)
        self.assertEqual(slot_to_plan.allocated_hours, 5)
        copy_start = start + timedelta(weeks=1)
        PlanningSlot.action_copy_previous_week(
            str(copy_start.replace(tzinfo=None)),
            [],
        )
        copy = PlanningSlot.search([
            ('start_datetime', '=', copy_start),
            ('sale_line_id', '=', sol.id),
        ])
        self.assertEqual(len(copy), 1)
        self.assertFalse(slot_to_plan.exists())
        PlanningSlot = PlanningSlot.with_context(
            default_start_datetime='2021-07-25 00:00:00',
            default_end_datetime='2021-07-31 23:59:59',
            scale='week',
            focus_date='2021-07-31 00:00:00',
            planning_gantt_active_sale_order_id=so.id,
        )
        shifts = PlanningSlot.auto_plan_ids([('start_datetime', '=', '2019-07-01 00:00:00'), ('end_datetime', '=', '2019-07-07 23:59:59')])
        self.assertEqual(len(shifts), 0)

    def test_add_to_compute_then_create_field(self):
        so = self.env['sale.order'].create({
            "partner_id": self.planning_partner.id,
        })
        sol = self.env['sale.order.line'].create({
            "product_id": self.plannable_product.id,
            "product_uom_qty": 10,
            "order_id": so.id,
        })
        so.action_confirm()

        self.env['planning.slot'].create({
            'sale_line_id': sol.id,
        })

        sol.env.flush_all()

        # call Model._setup_base => no error because of add_to_compute in compute should happen
        field = self.env['ir.model.fields'].create({
            'name': 'x_this_is_a_test',
            'model_id': self.env['ir.model'].search([('model', '=', 'planning.slot')]).id,
            'field_description': 'foo',
            'ttype': 'integer',
        })
        field.unlink()
