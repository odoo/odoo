# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


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
        partners_format = super(ResPartner, self).mail_partner_format()
        main_user_ids = set(partner_format['user_id'] for partner_format in partners_format.values())
        for partner in self:
            main_user = self.env['res.users'].browse(partners_format.get(partner)['user_id']).with_prefetch(main_user_ids)
            partners_format.get(partner).update({
                'out_of_office_date_end': main_user.leave_date_to,
            })
        return partners_format

    @api.model
    def _get_on_leave_ids(self):
        return self.env['res.users']._get_on_leave_ids(partner=True)
