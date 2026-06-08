# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', 'Time Type',
        domain="[('id', 'in', allowed_work_entry_type_ids)]",
        groups="hr.group_hr_user")
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids')

    @api.depends('calendar_id.company_id', 'company_id')
    def _compute_allowed_work_entry_type_ids(self):
        for leave in self:
            country = leave.calendar_id.company_id.country_id or leave.company_id.country_id or self.env.company.country_id
            if not country or not self.env['hr.work.entry.type'].search_count([('country_id', '=', country.id)], limit=1):
                domain = [('country_id', '=', False)]
            else:
                domain = [('country_id', '=', country.id)]
            leave.allowed_work_entry_type_ids = self.env['hr.work.entry.type'].search(domain)

    def _copy_leave_vals(self):
        res = super()._copy_leave_vals()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res
