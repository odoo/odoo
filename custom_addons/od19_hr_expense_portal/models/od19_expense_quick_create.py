# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Od19ExpenseQuickCreate(models.TransientModel):
    _name = 'od19.expense.quick.create'
    _description = 'Quick Expense Submission Wizard'

    expense_category_id = fields.Many2one(
        'product.product',
        string='Category / หมวดค่าใช้จ่าย',
        required=True,
        domain="[('can_be_expensed', '=', True)]",
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee / พนักงาน',
        required=True,
        default=lambda self: self.env.user.employee_id,
    )
    expense_date = fields.Date(
        string='Expense Date / วันที่',
        default=fields.Date.context_today,
        required=True,
    )
    description = fields.Char(
        string='Description / รายละเอียด',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id.id,
    )
    # Flag computed (read-only) from the chosen category so the wizard never
    # writes back to the product. See plan constraint C7.
    od19_is_mileage = fields.Boolean(
        string='Mileage / ค่าเดินทางตามระยะทาง',
        compute='_compute_od19_is_mileage',
    )
    amount = fields.Monetary(
        string='Amount / จำนวนเงิน',
        currency_field='currency_id',
    )
    distance_km = fields.Float(
        string='Distance (km) / ระยะทาง (กม.)',
    )
    vehicle_id = fields.Many2one(
        'od19.employee.vehicle',
        string='Vehicle / รถของฉัน',
    )
    od19_mileage_rate = fields.Monetary(
        string='Rate / km / อัตราต่อ กม.',
        currency_field='currency_id',
        compute='_compute_od19_mileage_rate',
    )
    total_amount = fields.Monetary(
        string='Total / ยอดรวม',
        currency_field='currency_id',
        compute='_compute_total_amount',
    )
    origin = fields.Char(
        string='Origin / ต้นทาง',
    )
    destination = fields.Char(
        string='Destination / ปลายทาง',
    )
    submit_now = fields.Boolean(
        string='Submit now / ส่งอนุมัติทันที',
        default=True,
    )

    @api.depends('expense_category_id')
    def _compute_od19_is_mileage(self):
        for wiz in self:
            wiz.od19_is_mileage = (
                wiz.expense_category_id.od19_is_mileage_category
            )

    @api.depends('od19_is_mileage')
    def _compute_od19_mileage_rate(self):
        rate = self.env.company.od19_mileage_rate
        for wiz in self:
            wiz.od19_mileage_rate = rate if wiz.od19_is_mileage else 0.0

    @api.depends('od19_is_mileage', 'distance_km', 'amount',
                 'od19_mileage_rate')
    def _compute_total_amount(self):
        for wiz in self:
            wiz.total_amount = (
                (wiz.distance_km or 0.0) * (wiz.od19_mileage_rate or 0.0)
                if wiz.od19_is_mileage else (wiz.amount or 0.0)
            )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Default the vehicle to the employee's most recently used one."""
        for wiz in self:
            if wiz.employee_id and not wiz.vehicle_id:
                wiz.vehicle_id = self.env['od19.employee.vehicle'].search(
                    [('employee_id', '=', wiz.employee_id.id)], limit=1)

    def action_create_expense(self):
        """Create the ``hr.expense`` and optionally submit it for approval."""
        self.ensure_one()
        vals = {
            'employee_id': self.employee_id.id,
            'product_id': self.expense_category_id.id,
            'date': self.expense_date or fields.Date.context_today(self),
        }
        if self.description:
            vals['name'] = self.description
        if self.od19_is_mileage:
            distance = self.distance_km or 0.0
            rate = self.env.company.od19_mileage_rate
            # price_unit is read-only in core: drive the amount through
            # quantity (= km) and total_amount (= km x rate) so core derives
            # price_unit for the no-cost mileage category.
            vals.update({
                'od19_is_mileage': True,
                'od19_mileage_distance_km': distance,
                'od19_mileage_vehicle_id': self.vehicle_id.id,
                'od19_mileage_origin': self.origin,
                'od19_mileage_destination': self.destination,
                'od19_mileage_date': self.expense_date,
                'quantity': distance,
                'total_amount': distance * rate,
            })
        else:
            vals['total_amount'] = self.amount
        expense = self.env['hr.expense'].create(vals)
        if self.submit_now:
            expense.action_submit()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expense',
            'res_model': 'hr.expense',
            'res_id': expense.id,
            'view_mode': 'form',
            'target': 'current',
        }
