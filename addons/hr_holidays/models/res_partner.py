# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


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

    def mail_partner_format(self):
        now = fields.Datetime.now()
        leaves = self.env['hr.leave'].sudo().search([
            ('user_id.partner_id', 'in', self.ids),
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', now),
            ('date_to', '>=', now),
        ])
        leave_per_partner = {leave.user_id.partner_id: leave for leave in leaves}
        partners_format = super(ResPartner, self).mail_partner_format()
        for partner in self:
            partners_format.get(partner).update({
                'out_of_office_date_end': leave_per_partner.get(partner, self.env['hr.leave']).date_to
            })
        return partners_format

    @api.model
    def _get_on_leave_ids(self):
        return self.env['res.users']._get_on_leave_ids(partner=True)
