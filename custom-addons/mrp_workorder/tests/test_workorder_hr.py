#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from freezegun import freeze_time

from odoo import Command
from odoo.tests import Form, common

class TestWorkorderDurationHr(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'groups_id': [(4, grp_workorder.id)]})
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter',
            'employee_ids': [
                Command.create({
                    'name': 'Qian Xuesen',
                    'pin': '1234'}),
                Command.create({
                    'name': 'Yu Min',
                    'pin': '5678'})]})
        cls.employee_1 = cls.workcenter.employee_ids[0]
        cls.employee_2 = cls.workcenter.employee_ids[1]
        cls.final_product = cls.env['product.product'].create({
            'name': 'DF-41',
            'type': 'product',
            'tracking': 'none'})
        cls.component = cls.env['product.product'].create({
            'name': 'RBCC engine',
            'type': 'product',
            'tracking': 'none'})
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({
                    'name': 'fuel injection',
                    'workcenter_id': cls.workcenter.id,
                    'time_cycle': 12,
                    'sequence': 1})]})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.component.id,
            'product_qty': 1.0,
            'bom_id': cls.bom.id})
        mo_form = Form(cls.env['mrp.production'])
        mo_form.product_id = cls.final_product
        mo_form.bom_id = cls.bom
        mo_form.product_qty = 1
        cls.mo = mo_form.save()

    def test_workorder_duration(self):
        """Test the duration of workorder is computed based on employee time interval
        """
        self.mo.action_confirm()
        wo = self.mo.workorder_ids[0]
        with freeze_time('2027-10-01 10:00:00'):
            wo.start_employee(self.employee_1.id)
            self.env.flush_all()   # need flush to trigger compute
        with freeze_time('2027-10-01 11:00:00'):
            wo.stop_employee([self.employee_1.id])
            self.env.flush_all()   # need flush to trigger compute
        self.assertEqual(wo.duration, 60)

        # add new time interval that overlapped with the previous one
        wo_form = Form(wo)
        with wo_form.time_ids.new() as line:
            line.employee_id = self.employee_2
            line.date_start = datetime(2027, 10, 1, 10, 30, 0)
            line.date_end = datetime(2027, 10, 1, 11, 30, 0)
            line.loss_id = self.env.ref('mrp.block_reason7')
        wo_form.save()
        self.assertEqual(wo.duration, 90)

        # add new time interval that not overlapped with the previous ones
        with wo_form.time_ids.new() as line:
            line.employee_id = self.employee_1
            line.date_start = datetime(2027, 10, 1, 12, 30, 0)
            line.date_end = datetime(2027, 10, 1, 13, 30, 0)
            line.loss_id = self.env.ref('mrp.block_reason7')
        wo_form.save()
        self.assertEqual(wo.duration, 150)
