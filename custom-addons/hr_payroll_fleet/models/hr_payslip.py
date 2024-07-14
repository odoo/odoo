# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import AccessError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()

        try:
            self.env['fleet.vehicle'].check_access_rights('read')
            self.env['fleet.vehicle.log.contract'].check_access_rights('read')
        except AccessError:
            return res

        self.env.cr.execute("""
            SELECT v.id
              FROM fleet_vehicle v
             WHERE v.driver_employee_id IS NOT NULL
               AND NOT EXISTS (SELECT 1
                                 FROM fleet_vehicle_log_contract c
                                WHERE c.vehicle_id = v.id
                                  AND c.company_id = v.company_id
                                  AND c.active IS TRUE
                                  AND c.state = 'open')
               AND v.company_id IN %s
               AND v.active IS TRUE
          GROUP BY v.id
        """, (tuple(self.env.companies.ids), ))
        vehicles_no_contract = [vid[0] for vid in self.env.cr.fetchall()]

        if vehicles_no_contract:
            no_contract = _('Vehicles With Drivers And Without Running Contract')
            res.append({
                'string': no_contract,
                'count': len(vehicles_no_contract),
                'action': self._dashboard_default_action(no_contract, 'fleet.vehicle', vehicles_no_contract),
            })

        self.env.cr.execute("""
            SELECT driver_employee_id
              FROM fleet_vehicle
             WHERE active IS TRUE
               AND company_id IN %s
          GROUP BY driver_employee_id
            HAVING COUNT(driver_employee_id) > 1
        """, (tuple(self.env.companies.ids), ))
        employees_multiple_vehicles = [eid[0] for eid in self.env.cr.fetchall()]

        if employees_multiple_vehicles:
            multiple_vehicles = _('Employees With Multiple Company Cars')
            res.append({
                'string': multiple_vehicles,
                'count': len(employees_multiple_vehicles),
                'action': self._dashboard_default_action(multiple_vehicles, 'hr.employee', employees_multiple_vehicles),
            })

        return res
