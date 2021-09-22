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

    def mail_partner_format(self):
        """Override to add the current leave status."""
        partners_format = super().mail_partner_format()
        for partner in self:
            # in the rare case of multi-user partner, return the earliest possible return date
            dates = partner.mapped('user_ids.leave_date_to')
            date = sorted(dates)[0] if dates and all(dates) else False
            partners_format.get(partner).update({
                'out_of_office_date_end': date.strftime(DEFAULT_SERVER_DATE_FORMAT) if date else False,
            })
        return partners_format
