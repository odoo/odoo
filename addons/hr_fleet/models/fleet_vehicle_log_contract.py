# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class FleetVehicleLogContract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    purchaser_employee_id = fields.Many2one(
        'hr.employee',
        string='Driver (Employee)',
        compute='_compute_purchaser_employee_id',
        store=True,
    )

    @api.depends('purchaser_id', 'vehicle_id')
    def _compute_purchaser_employee_id(self):
        other_drivers = self.filtered(lambda c: c.purchaser_id != c.vehicle_id.driver_id).purchaser_id
        employees_by_partner_and_company = {
            (partner, company): employees
            for partner, company, employees in self.env['hr.employee']._read_group(
                domain=[('work_contact_id', 'in', other_drivers.ids)],
                groupby=['work_contact_id', 'company_id'],
                aggregates=['id:recordset'],
            )
        }
        employees_by_partner = {
            partner: employees for (partner, _company), employees in employees_by_partner_and_company.items()
        }
        for contract in self:
            if contract.purchaser_id == contract.vehicle_id.driver_id:
                contract.purchaser_employee_id = contract.vehicle_id.driver_employee_id
                continue
            employees = (
                employees_by_partner_and_company.get((contract.purchaser_id, contract.company_id))
                or employees_by_partner.get(contract.purchaser_id)
            )
            contract.purchaser_employee_id = employees[:1] if employees else False

    def action_open_employee(self):
        self.ensure_one()
        return {
            'name': _('Related Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.purchaser_employee_id.id,
        }
