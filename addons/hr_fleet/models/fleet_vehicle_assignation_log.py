# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetVehicleAssignationLog(models.Model):
    _inherit = 'fleet.vehicle.assignation.log'

    driver_employee_id = fields.Many2one('hr.employee', string='Driver (Employee)', compute='_compute_driver_employee_id', store=True, readonly=False)
    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')
    driver_employee_date_start = fields.Date(string="Drier Employee Start Date", compute='_compute_driver_employee_id', store=True)
    driver_employee_date_end = fields.Date(string="Driver Employee End Date", compute='_compute_driver_employee_id', store=True)

    @api.depends('driver_id', 'date_start', 'date_end')
    def _compute_driver_employee_id(self):
        employees_by_partner_id_and_company_id = self.env['hr.employee']._read_group(
            domain=[('work_contact_id', 'in', self.driver_id.ids)],
            groupby=['work_contact_id', 'company_id'],
            aggregates=['id:recordset']
        )
        employees_by_partner_id_and_company_id = {
            (partner, company): employee for partner, company, employee in employees_by_partner_id_and_company_id
        }
        for log in self:
            employees = employees_by_partner_id_and_company_id.get((log.driver_id, log.vehicle_id.company_id))
            log.driver_employee_id = employees[0] if employees else False
            log.driver_employee_date_start = log.date_start
            log.driver_employee_date_end = log.date_end

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment']._read_group([
            ('res_model', '=', 'fleet.vehicle.assignation.log'),
            ('res_id', 'in', self.ids)], ['res_id'], ['__count'])
        attachment = dict(attachment_data)
        for doc in self:
            doc.attachment_number = attachment.get(doc.id, 0)

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['views'] = [[self.env.ref('hr_fleet.view_attachment_kanban_inherit_hr').id, 'kanban']]
        res['domain'] = [('res_model', '=', 'fleet.vehicle.assignation.log'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'fleet.vehicle.assignation.log', 'default_res_id': self.id}
        return res
