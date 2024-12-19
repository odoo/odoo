# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.mail.tools.discuss import Store
from datetime import date as d

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
                elif partner.im_status == 'offline':
                    partner.im_status = 'leave_offline'

    @api.model
    def _get_on_leave_ids(self):
        return self.env['res.users']._get_on_leave_ids(partner=True)

    def _to_store_defaults(self):
        today = d.today()
        def out_of_office_date_end(partner):
            if partner.user_ids:
                public_holiday = partner.user_ids.employee_id.get_public_holidays_data(today, today)
                if public_holiday:
                    return "public_holiday"
            # in the rare case of multi-user partner, return the earliest possible return date
            dates = partner.mapped("user_ids.leave_date_to")
            states = partner.mapped("user_ids.current_leave_state")
            date = sorted(dates)[0] if dates and all(dates) else False
            state = sorted(states)[0] if states and all(states) else False
            return date if state == "validate" else False

        return super()._to_store_defaults() + [
            Store.Attr("out_of_office_date_end", out_of_office_date_end)
        ]
