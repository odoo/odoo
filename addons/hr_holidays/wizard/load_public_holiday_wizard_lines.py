# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo
from odoo.tools.date_utils import convert_timezone


class ResourceCalendarPublicHolidayWizardLine(models.TransientModel):
    _name = 'load.public.holiday.wizard.line'
    _description = 'Public Holiday Preview Wizard Line'
    _order = 'company_id, start_date, name'

    name = fields.Char(required=True)
    wizard_id = fields.Many2one('load.public.holiday.wizard', required=True, ondelete='cascade')
    start_date = fields.Date(required=True)
    company_id = fields.Many2one('res.company', required=True)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string="Time Type",
        compute='_compute_work_entry_type', readonly=False, store=True,
        domain="[('id', 'in', allowed_work_entry_type_ids)]")
    allowed_work_entry_type_ids = fields.Many2many('hr.work.entry.type', compute='_compute_work_entry_type', store=True)

    @api.depends('company_id')
    def _compute_work_entry_type(self):
        allowed_work_entry_types = self.env['hr.work.entry.type'].search([
            '|',
            ('country_id', 'in', self.company_id.country_id.ids),
            ('country_id', '=', False),
        ])
        public_holiday_work_entry_types = allowed_work_entry_types.filtered_domain([('code', '=', '006.00')])
        for line in self:
            country = line.company_id.country_id
            if not country or not allowed_work_entry_types.filtered_domain([('country_id', '=', country.id)]):
                domain = [('country_id', '=', False)]
            else:
                domain = [('country_id', '=', country.id)]
            line.allowed_work_entry_type_ids = allowed_work_entry_types.filtered_domain(domain)
            line.work_entry_type_id = public_holiday_work_entry_types.filtered_domain(domain)

    def _prepare_leave_values(self):
        self.ensure_one()
        company = self.company_id
        company_tz = ZoneInfo(company.tz or 'UTC')
        create_values = {
            'name': self.name,
            'date_from': convert_timezone(datetime.combine(self.start_date, time.min), UTC, company_tz),
            'date_to': convert_timezone(datetime.combine(self.start_date, time.max), UTC, company_tz),
            'company_id': company.id,
        }
        work_entry_type = self.work_entry_type_id
        if work_entry_type:
            create_values.update({
                'work_entry_type_id': work_entry_type.id,
                'count_as': work_entry_type.count_as,
                'elligible_for_accrual_rate': work_entry_type.elligible_for_accrual_rate,
            })
        return create_values
