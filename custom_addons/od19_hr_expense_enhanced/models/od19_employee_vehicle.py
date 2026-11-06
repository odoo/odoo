# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Od19EmployeeVehicle(models.Model):
    _name = 'od19.employee.vehicle'
    _description = 'Employee Vehicle Book'
    _order = 'od19_last_used_date desc, id desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee / พนักงาน',
        required=True,
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.user.employee_id,
    )
    od19_vehicle_type = fields.Selection(
        [
            ('car', 'Car / รถยนต์'),
            ('pickup', 'Pickup / กระบะ'),
            ('van', 'Van / ตู้'),
            ('motorcycle', 'Motorcycle / จักรยานยนต์'),
            ('other', 'Other / อื่น ๆ'),
        ],
        string='Vehicle Type / ประเภทยานพาหนะ',
        required=True,
        default='car',
    )
    od19_plate_number = fields.Char(
        string='Plate Number / ป้ายทะเบียน',
        required=True,
    )
    od19_last_used_date = fields.Date(
        string='Last Used / ใช้ล่าสุดเมื่อ',
    )
    active = fields.Boolean(default=True)

    _od19_vehicle_plate_uniq = models.Constraint(
        'unique(employee_id, od19_plate_number)',
        'This plate is already in the employee vehicle book.',
    )

    @api.depends('od19_plate_number', 'od19_vehicle_type')
    def _compute_display_name(self):
        for vehicle in self:
            type_label = dict(
                vehicle._fields['od19_vehicle_type'].selection
            ).get(vehicle.od19_vehicle_type)
            vehicle.display_name = (
                f"{vehicle.od19_plate_number} ({type_label})"
                if type_label else vehicle.od19_plate_number
            )
