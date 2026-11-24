# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', 'Time Type',
        domain="[('id', 'in', allowed_work_entry_type_ids)]",
        compute="_compute_work_entry_type_id",
        store=True, readonly=False,
        groups="hr.group_hr_user")
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids')

    @api.depends('calendar_id.company_id', 'company_id')
    def _compute_work_entry_type_id(self):
        """Default the type of global leaves to the public holiday type (``006.00``).

        The type of the leave's country is used, else the generic public holiday type. Leaves
        of a resource keep their type (set from the time off by ``hr_holidays``).
        """
        country_ids = [(leave.calendar_id.company_id.country_id or leave.company_id.country_id or self.env.company.country_id).id for leave in self]
        public_holiday_types = self.env['hr.work.entry.type'].search([
            ('code', '=', '006.00'),
            ('country_id', 'in', country_ids),
        ]).grouped('country_id')
        for leave in self:
            if leave.resource_id:
                continue
            country = leave.calendar_id.company_id.country_id or leave.company_id.country_id or self.env.company.country_id
            leave.work_entry_type_id = public_holiday_types.get(country, self.env.ref('hr_work_entry.generic_work_entry_type_public_holiday', raise_if_not_found=False))

    @api.depends('calendar_id.company_id', 'company_id')
    def _compute_allowed_work_entry_type_ids(self):
        countries = self.calendar_id.company_id.country_id | self.company_id.country_id | self.env.company.country_id
        # the types of the country, else the generic ones (country without types or no country)
        types_by_country = dict(self.env['hr.work.entry.type']._read_group(
            [('country_id', 'in', countries.ids + [False])],
            ['country_id'], ['id:recordset'],
        ))
        generic_types = types_by_country.get(self.env['res.country'], self.env['hr.work.entry.type'])
        for leave in self:
            country = leave.calendar_id.company_id.country_id or leave.company_id.country_id or self.env.company.country_id
            leave.allowed_work_entry_type_ids = types_by_country.get(country) or generic_types

    def _copy_leave_vals(self):
        res = super()._copy_leave_vals()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res
