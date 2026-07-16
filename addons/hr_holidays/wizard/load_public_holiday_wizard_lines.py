# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

WORK_ENTRY_TYPE_BY_COUNTRY = {
    'BE': 'hr_work_entry.l10n_be_work_entry_type_bank_holiday',
    'CH': 'hr_work_entry.l10n_ch_work_entry_type_bank_holiday',
    'HK': 'hr_work_entry.l10n_hk_work_entry_type_public_holiday',
}


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
        for line in self:
            allowed_work_entry_type = self.env['hr.work.entry.type'].search([
                ('country_id', '=', line.company_id.country_id.id)
            ])
            line.allowed_work_entry_type_ids = allowed_work_entry_type

            default_work_entry_type = False
            if xmlid := WORK_ENTRY_TYPE_BY_COUNTRY.get(line.company_id.country_id.code):
                default_work_entry_type = self.env.ref(xmlid, raise_if_not_found=False)

            line.work_entry_type_id = (
                default_work_entry_type
                if default_work_entry_type and default_work_entry_type in allowed_work_entry_type
                else False
            )
