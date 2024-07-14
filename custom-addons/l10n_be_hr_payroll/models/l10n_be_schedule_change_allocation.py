# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import api, models, fields, _


class L10nBeScheduleChangeAllocation(models.Model):
    _name = 'l10n_be.schedule.change.allocation'
    _description = 'Update allocation on schedule change'

    effective_date = fields.Date(required=True)
    contract_id = fields.Many2one(
        'hr.contract',
        required=True,
        ondelete='cascade',
    )
    leave_allocation_id = fields.Many2one(
        'hr.leave.allocation',
        required=True,
        ondelete='cascade',
    )
    maximum_days = fields.Float()
    current_resource_calendar_id = fields.Many2one(
        'resource.calendar',
        required=True,
        ondelete='cascade',
    )
    new_resource_calendar_id = fields.Many2one(
        'resource.calendar',
        required=True,
        ondelete='cascade',
    )

    def apply_directly(self):
        for record in self:
            # Avoid updating the number of days if the contract has been cancelled
            # Contrat may not be open already, it depends on another cron
            if record.contract_id.state in ['draft', 'open']:
                number_of_days = self.env['l10n_be.hr.payroll.schedule.change.wizard']\
                    .with_company(record.contract_id.company_id)._compute_new_allocation(
                        record.leave_allocation_id, record.current_resource_calendar_id,
                        record.new_resource_calendar_id, record.effective_date,
                )
                record.leave_allocation_id.write({
                    'number_of_days': number_of_days,
                })
                record.leave_allocation_id._message_log(body=Markup(_('New working schedule on %(contract_name)s.<br/>'
                'New total: %(days)s')) % {'contract_name': record.contract_id.name, 'days': number_of_days})

    @api.model
    def _cron_update_allocation_from_new_schedule(self, date=None):
        if not date:
            date = fields.Date.today()
        to_apply = self.search([('effective_date', '<=', date)])
        to_apply.apply_directly()
        to_apply.unlink()
