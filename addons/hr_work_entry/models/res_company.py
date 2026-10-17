# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_code = fields.Char("External Code", groups="hr.group_hr_user", copy=False, help="Use this code to export your data to a third party")
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids')

    def _get_default_attendance_work_entry_type(self):
        self.ensure_one()
        country_code = (self.country_id or self.env.company.country_id).code
        country_type = self.env['hr.work.entry.type'].search([
            ('code', '=', '002.00'),
            ('country_code', '=', country_code),
        ], limit=1)
        return country_type

    @api.depends('partner_id.country_id')
    def _compute_allowed_work_entry_type_ids(self):
        for company in self:
            country = company.country_id or self.env.company.country_id
            company.allowed_work_entry_type_ids = self.env['hr.work.entry.type'].search([('country_id', '=', country.id)])
