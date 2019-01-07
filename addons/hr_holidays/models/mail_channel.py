# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Channel(models.Model):
    _inherit = 'mail.channel'

    @api.multi
    def channel_info(self, extra_info=False):
        channel_infos = super(Channel, self).channel_info(extra_info)
        partners_on_leave = []
        for channel_info in channel_infos:
            if 'direct_partner' in channel_info:
                for direct_partner in channel_info['direct_partner']:
                    if 'leave' in direct_partner['im_status']:
                        partners_on_leave.append(direct_partner['id'])
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
            out_of_office_info = dict(((res['partner_id'], res) for res in self.env.cr.dictfetchall()))
            for channel_info in channel_infos:
                if 'direct_partner' in channel_info:
                    for direct_partner in channel_info['direct_partner']:
                        if 'leave' in direct_partner['im_status']:
                            direct_partner['out_of_office_date_end'] = out_of_office_info.get(direct_partner['id'], {}).get('date_to')
                            direct_partner['out_of_office_message'] = out_of_office_info.get(direct_partner['id'], {}).get('out_of_office_message')
        return channel_infos
