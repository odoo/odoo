# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_code = fields.Char("External Code", groups="hr.group_hr_user", copy=False, help="Use this code to export your data to a third party")
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids')

    @api.model_create_multi
    def create(self, vals_list):
        # before super(): stored computes depending on country_id must find the copy already there.
        self._copy_generic_attendance_work_entry_type(self._get_countries_from_vals(vals_list))
        return super().create(vals_list)

    def write(self, vals):
        self._copy_generic_attendance_work_entry_type(self._get_countries_from_vals([vals]))
        return super().write(vals)

    @api.model
    def _get_countries_from_vals(self, vals_list):
        # country_id may be given as an id or as a record
        country_field = self._fields['country_id']
        return self.env['res.country'].browse(list({
            country_field.convert_to_cache(vals['country_id'], self)
            for vals in vals_list if vals.get('country_id')
        }))

    @api.model
    def _copy_generic_attendance_work_entry_type(self, countries):
        """Give each of ``countries`` without any time type of its own (not localized) a copy of
        the generic attendance time type (``002.00``), so its companies have one to default to.

        :param res.country countries: the countries to check
        """
        if not countries:
            return
        generic_attendance = self.env.ref('hr_work_entry.generic_work_entry_type_attendance', raise_if_not_found=False)
        if not generic_attendance or generic_attendance.country_id:
            return
        generic_attendance = generic_attendance.sudo()
        WorkEntryType = self.env['hr.work.entry.type'].sudo().with_context(active_test=False)
        covered_countries = WorkEntryType.search([('country_id', 'in', countries.ids)]).country_id
        for country in countries - covered_countries:
            # code and name (in every language) passed explicitly: copy() suffixes them otherwise
            generic_attendance.copy({
                'code': generic_attendance.code,
                'name': generic_attendance._get_stored_translations('name'),
                'country_id': country.id,
            })

    def _get_default_attendance_work_entry_type(self):
        """Return the ``002.00`` (attendance) work entry type of the company's country."""
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
