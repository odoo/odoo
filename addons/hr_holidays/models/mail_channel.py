# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Channel(models.Model):
    _inherit = 'mail.channel'

    def partner_info(self, all_partners, direct_partners):
        partner_infos = super(Channel, self).partner_info(all_partners, direct_partners)
        # only search for leave out_of_office_message if im_status is on leave
        partners_on_leave = [partner_id for partner_id in direct_partners.ids if 'leave' in partner_infos[partner_id]['im_status']]
        if partners_on_leave:
            now = fields.Datetime.now()
            self.env.cr.execute('''SELECT res_users.partner_id as partner_id, hr_leave.out_of_office_message as out_of_office_message, hr_leave.date_to as date_to
                                FROM res_users
                                JOIN hr_leave ON hr_leave.user_id = res_users.id
                                AND hr_leave.state not in ('cancel', 'refuse')
                                AND res_users.active = 't'
                                AND hr_leave.date_from <= %s
                                AND hr_leave.date_to >= %s
                                AND res_users.partner_id in %s''', (now, now, tuple(partners_on_leave)))
            out_of_office_infos = dict(((res['partner_id'], res) for res in self.env.cr.dictfetchall()))
            for partner_id, out_of_office_info in out_of_office_infos.items():
                partner_infos[partner_id]['out_of_office_date_end'] = out_of_office_info['date_to']
                partner_infos[partner_id]['out_of_office_message'] = out_of_office_info['out_of_office_message']
        return partner_infos
