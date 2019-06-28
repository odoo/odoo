# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Channel(models.Model):
    _inherit = 'mail.channel'

    def partner_info(self, all_partners, direct_partners):
        partner_infos = super(Channel, self).partner_info(all_partners, direct_partners)
        # only search for leave out_of_office_message if im_status is on leave
        partners_on_leave = [partner_id for partner_id in direct_partners.ids if 'leave' in partner_infos[partner_id]['im_status']]
        if partners_on_leave:
            for user in self.env['res.users'].sudo().search([('partner_id', 'in', partners_on_leave)]):
                partner_infos[user.partner_id.id]['out_of_office_date_end'] = user.leave_consolidated_date_to

        return partner_infos
