# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrWorkEntryType(models.Model):
    _name = 'hr.work.entry.type'
    _description = 'HR Work Entry Type'

    name = fields.Char(required=True, translate=True)
    display_code = fields.Char(string="Display Code", size=3, translate=True, help="This code can be changed, it is only for a display purpose (3 letters max)")
    code = fields.Char(string="Payroll Code", required=True, help="Careful, the Code is used in many references, changing it could lead to unwanted changes.")
    external_code = fields.Char(help="Use this code to export your data to a third party")
    color = fields.Integer(default=0)
    sequence = fields.Integer(default=25)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to false, it will allow you to hide the work entry type without removing it.")
    country_id = fields.Many2one(
        'res.country',
        string="Country",
        domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)]
    )
    country_code = fields.Char(related='country_id.code')
    is_leave = fields.Boolean(
        default=False, string="Time Off", help="Allow the work entry type to be linked with time off types.")
    is_work = fields.Boolean(
        compute='_compute_is_work', inverse='_inverse_is_work', string="Working Time", readonly=False,
        help="If checked, the work entry is counted as work time in the working schedule")
    amount_rate = fields.Float(
        string="Rate",
        default=1.0,
        help="If you want the hours should be paid double, the rate should be 200%.")
    is_extra_hours = fields.Boolean(
        string="Added to Monthly Pay",
        help="Check this setting if you want the hours to be considered as extra time and added as a bonus to the basic salary.")

    @api.constrains('country_id')
    def _check_work_entry_type_country(self):
        if self.env.ref('hr_work_entry.work_entry_type_attendance') in self:
            raise UserError(_("You can't change the country of this specific work entry type."))
        elif not self.env.context.get('install_mode') and self.env['hr.work.entry'].sudo().search_count([('work_entry_type_id', 'in', self.ids)], limit=1):
            raise UserError(_("You can't change the Country of this work entry type cause it's currently used by the system. You need to delete related working entries first."))

    @api.constrains('code', 'country_id')
    def _check_code_unicity(self):
        similar_work_entry_types = self.search([
            ('code', 'in', self.mapped('code')),
            ('country_id', 'in', self.country_id.ids + [False]),
            ('id', 'not in', self.ids)
        ])
        for work_entry_type in self:
            invalid_work_entry_types = similar_work_entry_types.filtered_domain([
                ('code', '=', work_entry_type.code),
                ('country_id', 'in', self.country_id.ids + [False]),
            ])
            if invalid_work_entry_types:
                raise UserError(_("The same code cannot be associated to multiple work entry types (%s)", ', '.join(list(set(invalid_work_entry_types.mapped('code'))))))

    @api.depends('is_leave')
    def _compute_is_work(self):
        for record in self:
            record.is_work = not record.is_leave

    def _inverse_is_work(self):
        for record in self:
            record.is_leave = not record.is_work
