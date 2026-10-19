# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, common, new_test_user
from odoo import fields


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestFleet(common.TransactionCase):

    def test_search_renewal(self):
        """
            Should find the car with overdue contract or renewal due soon
        """
        user = new_test_user(self.env, "test base user", groups="base.group_user")
        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        car_1 = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": user.partner_id.id,
            "plan_to_change_vehicle": False
        })

        car_2 = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": user.partner_id.id,
            "plan_to_change_vehicle": False
        })
        Log = self.env['fleet.vehicle.log.contract']
        Log.create({
            'vehicle_id': car_2.id,
            'expiration_date': fields.Date.add(fields.Date.today(), days=10)
        })
        res = self.env["fleet.vehicle"].search([('contract_renewal_due_soon', '=', True), ('id', '=', car_2.id)])
        self.assertEqual(res, car_2)

        Log.create({
            'vehicle_id': car_1.id,
            'expiration_date': fields.Date.add(fields.Date.today(), days=-10)
        })
        res = self.env["fleet.vehicle"].search([('contract_renewal_overdue', '=', True), ('id', '=', car_1.id)])
        self.assertEqual(res, car_1)

    def test_exclude_resolved_vehicles_from_overdue(self):
        """
            if there is an expired contract for the car, but it also has an open contract
            it should not be considered overdue
        """
        user = new_test_user(self.env, "test base user", groups="base.group_user")
        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        car_1 = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": user.partner_id.id,
            "plan_to_change_vehicle": False
        })

        Log = self.env['fleet.vehicle.log.contract']
        Log.create({
            'vehicle_id': car_1.id,
            'expiration_date': fields.Date.add(fields.Date.today(), days=-2)
        })
        Log.create({
            'vehicle_id': car_1.id,
            'expiration_date': fields.Date.add(fields.Date.today(), days=365)
        })

        res = self.env["fleet.vehicle"].search([('contract_renewal_overdue', '=', True), ('id', '=', car_1.id)])
        self.assertFalse(res)

    def test_done_contract_not_overdue(self):
        """ Ensure that a contract marked as done stops flagging its vehicle as overdue. """
        user = new_test_user(self.env, "test done user", groups="base.group_user")
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Audi"})
        model = self.env["fleet.vehicle.model"].create({"brand_id": brand.id, "name": "A3"})
        car_1 = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": user.partner_id.id,
            "plan_to_change_vehicle": False
        })
        # The contract ended 10 days ago, so the car should ask for an action.
        contract = self.env['fleet.vehicle.log.contract'].create({
            'vehicle_id': car_1.id,
            'expiration_date': fields.Date.add(fields.Date.today(), days=-10)
        })
        res = self.env["fleet.vehicle"].search([('contract_renewal_overdue', '=', True), ('id', '=', car_1.id)])
        self.assertEqual(res, car_1, "The expired contract should make the car overdue.")

        contract.action_done()
        self.assertEqual(contract.state, 'done', "The contract should be marked as done.")
        # A done contract carries no warning, so no day is left to count.
        self.assertEqual(contract.days_left, -1, "A done contract should not count remaining days.")

        res = self.env["fleet.vehicle"].search([('contract_renewal_overdue', '=', True), ('id', '=', car_1.id)])
        self.assertFalse(res, "The car should not be overdue once the contract is done.")
        self.assertEqual(car_1.contract_state, 'done', "The car should show the done contract state.")

        # The daily cron must leave done contracts alone instead of expiring them again.
        self.env['fleet.vehicle.log.contract'].scheduler_manage_contract_expiration()
        self.assertEqual(contract.state, 'done', "The cron should not reopen a done contract.")
