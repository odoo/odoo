# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_im_status(self):
        super(ResPartner, self)._compute_im_status()
        absent_now = self._get_on_leave_ids()
        for partner in self:
            if partner.id in absent_now:
                if partner.im_status == 'online':
                    partner.im_status = 'leave_online'
                elif partner.im_status == 'away':
                    partner.im_status = 'leave_away'
                else:
                    partner.im_status = 'leave_offline'

    @api.model
    def _get_on_leave_ids(self):
        return self.env['res.users']._get_on_leave_ids(partner=True)

    def mail_partner_format(self, fields=None):
        """Override to add the current leave status."""
        partners_format = super().mail_partner_format(fields=fields)
        if not fields or 'out_of_office_date_end' in fields:
            out_of_office_date_end = self._get_out_of_office_date_end()
            for partner, date, state in out_of_office_date_end:
                partners_format.get(partner).update({
                    'out_of_office_date_end': date.strftime(DEFAULT_SERVER_DATE_FORMAT) if state == 'validate' and date else False,
                })
        return partners_format

    def _get_out_of_office_date_end(self):
        out_of_office_data = []
        # sudo: any user can access the leave state of any employee for the out of office
        all_employees_sudo = self.env["hr.employee"].sudo().search_fetch(
            domain=[("user_partner_id", "in", self.ids)],
            field_names=["leave_date_to", "current_leave_state", "user_partner_id", "company_id"],
        )
        for partner in self:
            employees_partner = all_employees_sudo.filtered(lambda emp: emp.user_partner_id == partner)
            if same_company_emp_sudo := employees_partner.sudo().filtered(lambda emp: emp.company_id in self.env.company):
                employees_partner = same_company_emp_sudo
            dates = employees_partner.mapped('leave_date_to')
            states = employees_partner.mapped('current_leave_state')
            date = sorted(dates)[0] if dates and all(dates) else False
            state = sorted(states)[0] if states and all(states) else False
            out_of_office_data.append((partner, date, state))
        return out_of_office_data
