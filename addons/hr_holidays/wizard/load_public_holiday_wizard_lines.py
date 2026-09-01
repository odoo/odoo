# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
