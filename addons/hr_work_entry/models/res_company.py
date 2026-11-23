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
        self._copy_generic_work_entry_types(self._get_countries_from_vals(vals_list))
        return super().create(vals_list)

    def write(self, vals):
        self._copy_generic_work_entry_types(self._get_countries_from_vals([vals]))
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
    def _get_generic_work_entry_types(self):
        """Return the generic (country-less) time types that every country must have its own
        copy of: attendance (``002.00``), out of contract (``000.00``) and public holiday
        (``006.00``). The code relies on them to fill in work entries and payslips.

        :rtype: hr.work.entry.type
        """
        # sudo: called when creating or writing a company, by users who can't read the time types
        generic_types = self.env['hr.work.entry.type'].sudo()
        for xmlid in (
            'hr_work_entry.generic_work_entry_type_attendance',
            'hr_work_entry.generic_hr_work_entry_type_out_of_contract',
            'hr_work_entry.generic_work_entry_type_public_holiday',
        ):
            generic_types |= (self.env.ref(xmlid, raise_if_not_found=False) or generic_types).sudo()
        return generic_types.filtered(lambda t: not t.country_id)

    @api.model
    def _copy_generic_work_entry_types(self, countries):
        """Give each of ``countries`` without a time type of its own for a code of
        :meth:`_get_generic_work_entry_types` a copy of the generic one, so its companies have
        one to default to.

        :param res.country countries: the countries to check
        """
        if not countries:
            return
        generic_types = self._get_generic_work_entry_types().sudo()
        if not generic_types:
            return
        WorkEntryType = self.env['hr.work.entry.type'].sudo().with_context(active_test=False)
        covered = {
            (code, country)
            for code, country in WorkEntryType._read_group(
                [('code', 'in', generic_types.mapped('code')), ('country_id', 'in', countries.ids)],
                groupby=['code', 'country_id'],
            )
        }
        for generic_type in generic_types:
            for country in countries:
                if (generic_type.code, country) in covered:
                    continue
                # code and name (in every language) passed explicitly: copy() suffixes them otherwise
                generic_type.copy({
                    'code': generic_type.code,
                    'name': generic_type._get_stored_translations('name'),
                    'country_id': country.id,
                })

    def _get_default_attendance_work_entry_type(self):
        """Return the ``002.00`` (attendance) work entry type of the company's country, else the
        generic one."""
        self.ensure_one()
        country_code = (self.country_id or self.env.company.country_id).code
        country_type = self.env['hr.work.entry.type'].search([
            ('code', '=', '002.00'),
            ('country_code', '=', country_code),
        ], limit=1)
        return country_type or self.env.ref('hr_work_entry.generic_work_entry_type_attendance', raise_if_not_found=False)

    @api.depends('partner_id.country_id')
    def _compute_allowed_work_entry_type_ids(self):
        for company in self:
            country = company.country_id or self.env.company.country_id
            company.allowed_work_entry_type_ids = self.env['hr.work.entry.type'].search([('country_id', '=', country.id)])
