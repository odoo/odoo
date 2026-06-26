# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_code = fields.Char("External Code", groups="hr.group_hr_user", copy=False, help="Use this code to export your data to a third party")
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids')

    def _get_default_attendance_work_entry_type(self):
        self.ensure_one()
        country_type = self.env['hr.work.entry.type'].search([
            ('code', '=', 'WORK100'),
            ('country_code', '=', self.country_id.code),
        ], limit=1)
        return country_type or self.env.ref('hr_work_entry.generic_work_entry_type_attendance', raise_if_not_found=False)

    @api.depends('partner_id.country_id')
    def _compute_allowed_work_entry_type_ids(self):
        for company in self:
            country = company.country_id or self.env.company.country_id
            if not country or not self.env['hr.work.entry.type'].search_count([('country_id', '=', country.id)], limit=1):
                domain = [('country_id', '=', False)]
            else:
                domain = [('country_id', '=', country.id)]
            company.allowed_work_entry_type_ids = self.env['hr.work.entry.type'].search(domain)
