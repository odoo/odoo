# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_planning.tests.test_sale_planning import TestSalePlanning


@tagged('post_install', '-at_install')
class TestRentalPlanning(TestSalePlanning):

    def test_planning_rental_sol_confirmation(self):
        plannable_employees = (
            plannable_employee1,
            plannable_employee2,
        ) = self.env['hr.employee'].create([
          {'name': 'employee 1'},
          {'name': 'employee 2'},
        ])
        self.env['resource.calendar.leaves'].create([{
            'name': 'leave',
            'date_from': datetime(2023, 10, 20, 8, 0),
            'date_to': datetime(2023, 10, 20, 17, 0),
            'resource_id': plannable_employee1.resource_id.id,
            'calendar_id': plannable_employee1.resource_calendar_id.id,
            'time_type': 'leave',
        }, {
            'name': 'Public Holiday',
            'date_from': datetime(2023, 10, 25, 0, 0, 0),
            'date_to': datetime(2023, 10, 25, 23, 59, 59),
            'calendar_id': plannable_employee1.resource_calendar_id.id,
        }])
        self.planning_role_junior.resource_ids = plannable_employees.resource_id
        self.plannable_product.rent_ok = True

        basic_so, resource_time_off_so, public_holiday_so = self.env['sale.order'].with_context(
            in_rental_app=True,
        ).create([{
            'partner_id': self.planning_partner.id,
            'rental_start_date': datetime(2023, 9, 25, 8, 0),
            'rental_return_date': datetime(2023, 9, 28, 8, 0),
            'order_line': [
                Command.create({
                    'product_id': self.plannable_product.id,
                    'product_uom_qty': 10,
                }),
            ],
        }, {
            'partner_id': self.planning_partner.id,
            'rental_start_date': datetime(2023, 10, 20, 8, 0),
            'rental_return_date': datetime(2023, 10, 20, 10, 0),
            'order_line': [
                Command.create({
                    'product_id': self.plannable_product.id,
                    'product_uom_qty': 10,
                }),
            ],
        }, {
            'partner_id': self.planning_partner.id,
            'rental_start_date': datetime(2023, 10, 25, 8, 0),
            'rental_return_date': datetime(2023, 10, 25, 15, 0),
            'order_line': [
                Command.create({
                    'product_id': self.plannable_product.id,
                    'product_uom_qty': 10,
                }),
            ],
        }])

        basic_so.action_confirm()
        slot = basic_so.order_line.planning_slot_ids

        self.assertTrue(slot.resource_id, 'Slot resource_id should not be False')
        self.assertEqual(slot.start_datetime, datetime(2023, 9, 25, 8, 0), 'Slot start datetime should be same as on SO')
        self.assertEqual(slot.end_datetime, datetime(2023, 9, 28, 8, 0), 'Slot end datetime should be same as on SO')

        self.assertEqual(basic_so.planning_hours_planned, 24.0, 'Planned hours should be set when the shift is already scheduled.')
        self.assertEqual(basic_so.planning_hours_to_plan, 0.0, 'To Plan hours should be zero when the shift is already scheduled.')

        resource_time_off_so.action_confirm()
        slot_2 = resource_time_off_so.order_line.planning_slot_ids

        self.assertEqual(slot_2.resource_id, plannable_employee2.resource_id, 'Second resource should be assign as first resource is on Time Off')

        plannable_employee1.resource_id.calendar_id = False
        public_holiday_so.action_confirm()
        slot_3 = public_holiday_so.order_line.planning_slot_ids

        self.assertEqual(slot_3.resource_id, plannable_employee1.resource_id, 'First resource should be assign on public holiday as first resource is working flexible hours')

    def test_planning_rental_for_material_resource(self):
        """
        Steps:
            1) Create a rental product with the `Plan Service` enabled and the resource type set to 'Material'.
            2) Create a SO for the newly created product and confirm it.
            3) Observe the state button the shift is already planned but it incorrectly displays 'To Plan'.
        """

        projector = self.env['resource.resource'].create({
            'name': 'Projector',
            'resource_type': 'material',
        })

        planning_role_projector = self.env['planning.role'].create({
            'name': 'Projector',
            'resource_ids': [(4, projector.id)],
        })

        product_projector = self.env['product.product'].create({
            'name': 'Projector Service',
            'type': 'service',
            'planning_enabled': True,
            'planning_role_id': planning_role_projector.id,
            'rent_ok': True,
        })

        so_rental = self.env['sale.order'].with_context(in_rental_app=True).create([{
            'partner_id': self.planning_partner.id,
            'rental_start_date': datetime(2024, 12, 18, 0, 0),
            'rental_return_date': datetime(2024, 12, 19, 0, 0),
            'order_line': [
                Command.create({
                    'product_id': product_projector.id,
                    'product_uom_qty': 10,
                }),
            ],
        }])

        so_rental.action_confirm()
        self.assertEqual(so_rental.planning_hours_planned, 8.0, 'Planned hours should be set when the shift is already scheduled.')
        self.assertEqual(so_rental.planning_hours_to_plan, 0.0, 'To Plan hours should be zero when the shift is already scheduled.')

    def test_planning_rental_sol_slot_conflict(self):
        '''
        Steps:
        1. Create a rental service product with `Plan Services` enabled.
        2. Create a rental order with multiple lines for the same product.
        3. Confirm the rental order.
        4. Check the generated shifts - each resource should have only one shift at a time
            if no resource available generate a open shift for that.
        '''
        self.planning_role_junior.resource_ids = [
            Command.set((self.employee_joseph.resource_id + self.employee_bert.resource_id).ids)
        ]
        self.plannable_product.rent_ok = True

        rental_order_1, rental_order_2 = self.env['sale.order'].with_context(in_rental_app=True).create([
            {
                'partner_id': self.planning_partner.id,
                'rental_start_date': datetime(2024, 12, 19, 9, 0),
                'rental_return_date': datetime(2024, 12, 19, 13, 0),
                'order_line': [
                    Command.create({'product_id': self.plannable_product.id, 'product_uom_qty': 1}),
                    Command.create({'product_id': self.plannable_product.id, 'product_uom_qty': 1}),
                ],
            }, {
                'partner_id': self.planning_partner.id,
                'rental_start_date': datetime(2024, 12, 26, 14, 0),
                'rental_return_date': datetime(2024, 12, 26, 17, 0),
                'order_line': [
                    Command.create({'product_id': self.plannable_product.id, 'product_uom_qty': 1}),
                    Command.create({'product_id': self.plannable_product.id, 'product_uom_qty': 1}),
                    Command.create({'product_id': self.plannable_product.id, 'product_uom_qty': 1}),
                ],
            },
        ])

        rental_order_1.action_confirm()
        ro_1_slots = rental_order_1.order_line.planning_slot_ids
        self.assertEqual(ro_1_slots.resource_id, self.employee_joseph.resource_id, 'The first shift should be assigned to joseph')
        self.assertEqual(len(ro_1_slots.filtered(lambda slot: not slot.resource_id)), 1, 'The second shift should be an open shift')

        rental_order_2.action_confirm()
        self.assertEqual(len(rental_order_2.order_line.planning_slot_ids.resource_id), 2,
                         'There should be 2 resources assigned to the shift')
