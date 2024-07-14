# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Company Car',
        compute='_compute_vehicle_id', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('contract_id.car_id.future_driver_id')
    def _compute_vehicle_id(self):
        for slip in self.filtered(lambda s: s.state not in ['done', 'cancel']):
            contract_sudo = slip.contract_id.sudo()
            if contract_sudo.car_id:
                future_driver = contract_sudo.car_id.future_driver_id
                if future_driver and future_driver == slip.employee_id.work_contact_id:
                    tmp_vehicle = self.env['fleet.vehicle'].search(
                        [('driver_id', '=', contract_sudo.car_id.future_driver_id.id)], limit=1)
                    slip.vehicle_id = tmp_vehicle
                else:
                    slip.vehicle_id = contract_sudo.car_id

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_be_hr_payroll_fleet', [
                'data/hr_rule_parameter_data.xml',
                'data/cp200_employee_salary_data.xml',
            ])]

    @api.model
    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()

        try:
            self.env['fleet.vehicle'].check_access_rights('read')
            self.env['fleet.vehicle.log.contract'].check_access_rights('read')
        except AccessError:
            return res

        self.env.cr.execute("""
            SELECT p.id
              FROM hr_payslip AS p
        INNER JOIN hr_contract AS c ON c.id = p.contract_id
             WHERE p.vehicle_id != c.car_id
                OR c.car_id IS NOT NULL AND p.vehicle_id IS NULL
                OR p.vehicle_id IS NOT NULL AND c.car_id IS NULL
               AND p.company_id IN %s
             GROUP BY p.id
        """, (tuple(self.env.companies.ids), ))

        payslips_with_different_cars_ids = [p[0] for p in self.env.cr.fetchall()]

        if payslips_with_different_cars_ids:
            message = _('Payslips with car different than on employee\'s contract')
            res.append({
                'string': message,
                'count': len(payslips_with_different_cars_ids),
                'action': self._dashboard_default_action(message, 'hr.payslip', payslips_with_different_cars_ids),
            })

        return res
