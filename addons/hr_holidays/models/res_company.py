from odoo import _, api, models, tools, modules
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_default_work_entry_type_values(self):
        vals_list = super()._get_default_work_entry_type_values()
        for vals in vals_list:
            if vals['count_as'] == 'working_time':
                # like the working time types of the data files (see hr_work_entry_type_data.xml)
                vals.update(requires_allocation=False, time_off_selectable=False, request_unit='hour')
        return vals_list

    @api.constrains('country_id')
    def _check_country_change_holidays(self):
        if tools.config['test_enable'] or modules.module.current_test:
            return
        for record in self:
            conflict_domain = [
                ('employee_company_id', '=', record.id),
                ('work_entry_type_id.country_id', '!=', False),
                ('work_entry_type_id.country_id', '!=', record.country_id.id),
            ]
            if (
                self.env['hr.leave'].search_count(conflict_domain, limit=1)
                or self.env['hr.leave.allocation'].search_count(conflict_domain, limit=1)
            ):
                raise ValidationError(_(
                    "The company country cannot be changed while time off leaves "
                    "or allocations with the country exist."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        self.env['resource.calendar.leaves']._cron_generate_public_holidays()
        return companies
