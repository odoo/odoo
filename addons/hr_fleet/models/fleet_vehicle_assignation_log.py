# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class FleetVehicleAssignationLog(models.Model):
    _inherit = 'fleet.vehicle.assignation.log'

    driver_employee_id = fields.Many2one('hr.employee', string='Driver (Employee)', compute='_compute_driver_employee_id', store=True, readonly=False)
    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')

    @api.depends('driver_id')
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

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("skip_driver_history"):
            return True  # To avoid recursion calls for this method when setting the driver_id
        records = super().create(vals_list)
        today = fields.Date.today()
        for rec in records:
            vehicle = rec.vehicle_id
            if (
                vehicle.driver_id
                or (rec.date_start and rec.date_start > today)
                or (rec.date_end and rec.date_end < today)
            ):
                continue
            vehicle.with_context(skip_driver_history=True).write({
                "driver_id": records.driver_id.id,
                "plan_to_change_vehicle": False,
            })

        return records

    @api.constrains('vehicle_id', 'date_start', 'date_end')
    def _check_date_overlap(self):
        for rec in self:
            base_domain = [('vehicle_id', '=', rec.vehicle_id.id), ('id', '!=', rec.id)]
            if rec.date_end:
                overlap_domain = Domain.OR([
                    Domain.AND([
                        Domain('date_start', '<', rec.date_end),
                        Domain.OR([
                            Domain('date_end', '>', rec.date_start),
                            Domain('date_end', '=', False),
                        ]),
                    ]),
                ])
            else:
                overlap_domain = Domain.OR([
                    Domain('date_end', '=', False),
                    Domain('date_end', '>', rec.date_start),
                ])
            domain = Domain.AND([base_domain, overlap_domain])

            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    self.env._(
                        "This assignment overlaps with an existing assignment for %(vehicle)s "
                        "(Driver: %(driver)s, Period: %(start)s to %(end)s)",
                        vehicle=rec.vehicle_id.name,
                        driver=overlapping.driver_id.name,
                        start=overlapping.date_start,
                        end=overlapping.date_end or self.env._('Ongoing')))
