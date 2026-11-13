# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_code = fields.Char("External Code", groups="hr.group_hr_user", copy=False, help="Use this code to export your data to a third party")
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids')

    @api.model_create_multi
    def create(self, vals_list):
        # before super(): stored computes depending on country_id must find the time type there.
        self._create_default_work_entry_types(self._get_vals_countries(vals_list))
        return super().create(vals_list)

    def write(self, vals):
        self._create_default_work_entry_types(self._get_vals_countries([vals]))
        return super().write(vals)

    @api.model
    def _get_vals_countries(self, vals_list):
        """Return the countries set by ``vals_list``, whatever the format of the value
        (id or record)."""
        country_field = self._fields['country_id']
        return self.env['res.country'].browse({
            country_field.convert_to_cache(vals['country_id'], self)
            for vals in vals_list if vals.get('country_id')
        } - {None})

    @api.model
    def _get_default_work_entry_type_values(self):
        """Return the values of the time types created for a country without localized ones.

        Override to complete them (e.g. ``hr_payroll`` adds the salary rule categories).

        :return: list of ``hr.work.entry.type`` values, without ``country_id``, whose ``name``
            is a lazy translation
        """
        return [{
            'name': _lt('Work'),
            'code': '002.00',
            'display_code': 'A',
            'color': 10,
            'count_as': 'working_time',
        }]

    @api.model
    def _create_default_work_entry_types(self, countries):
        """Give each of ``countries`` without any time type (not localized) the time types of
        :meth:`_get_default_work_entry_type_values`, so its companies have one to default to.

        :param res.country countries: the countries to check
        """
        if not countries:
            return
        WorkEntryType = self.env['hr.work.entry.type'].sudo().with_context(active_test=False)
        countries -= WorkEntryType.search([('country_id', 'in', countries.ids)]).country_id
        if not countries:
            return
        languages = [code for code, _name in self.env['res.lang'].get_installed() if code != 'en_US']
        for vals in self._get_default_work_entry_type_values():
            name = vals['name']
            work_entry_types = WorkEntryType.create([
                {**vals, 'name': name._translate('en_US'), 'country_id': country.id}
                for country in countries
            ])
            if languages:
                translations = {lang: name._translate(lang) for lang in languages}
                for work_entry_type in work_entry_types:
                    work_entry_type.update_field_translations('name', translations)

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
            company.allowed_work_entry_type_ids = self.env['hr.work.entry.type'].search([('country_id', 'in', country.ids)])
