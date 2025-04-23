# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_im_status(self):
        super()._compute_im_status()
        absent_now = self._get_on_leave_ids()
        for partner in self:
            if partner.id in absent_now:
                if partner.im_status == 'online':
                    partner.im_status = 'leave_online'
                elif partner.im_status == 'away':
                    partner.im_status = 'leave_away'
                elif partner.im_status == 'offline':
                    partner.im_status = 'leave_offline'

    @api.model
    def _get_on_leave_ids(self):
        return self.env['res.users']._get_on_leave_ids(partner=True)

    def get_mandatory_days_data(self, start_date, end_date, everybody):
        domain = self._get_data_domain(everybody)
        employee_ids = self.env['hr.employee'].search(domain).ids
        return self.env['hr.employee'].with_context({'employee_ids': employee_ids}).get_mandatory_days_data(start_date, end_date)

    def get_public_holidays_data(self, start_date, end_date, everybody):
        domain = self._get_data_domain(everybody)
        employee_ids = self.env['hr.employee'].search(domain).ids
        return self.env['hr.employee'].with_context({'employee_ids': employee_ids}).get_public_holidays_data(start_date, end_date)

    def _get_data_domain(self, everybody):
        if everybody:
            work_contact_id_domain = Domain('work_contact_id', '!=', False)
        else:
            work_contact_id_domain = Domain('work_contact_id', 'in', self.ids)
        domain = Domain.AND([work_contact_id_domain,Domain('company_id', '=', self.env.company.id)])
        return domain

    def _to_store_defaults(self):
        def out_of_office_date_end(partner):
            # in the rare case of multi-user partner, return the earliest possible return date
            dates = partner.mapped("user_ids.leave_date_to")
            states = partner.mapped("user_ids.current_leave_state")
            date = sorted(dates)[0] if dates and all(dates) else False
            state = sorted(states)[0] if states and all(states) else False
            return date if state == "validate" else False

        return super()._to_store_defaults() + [
            Store.Attr("out_of_office_date_end", out_of_office_date_end)
        ]
