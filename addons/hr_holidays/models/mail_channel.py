# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models


class Channel(models.Model):
    _inherit = 'mail.channel'

    def partner_info(self, all_partners, direct_partners):
        partner_infos = super(Channel, self).partner_info(all_partners, direct_partners)
        # only search for leave out_of_office_message if im_status is on leave
        partners_on_leave = [partner_id for partner_id in direct_partners.ids if 'leave' in partner_infos[partner_id]['im_status']]
        if partners_on_leave:
            now = fields.Datetime.now()
            self.env.cr.execute('''SELECT res_users.employee_id as employee_id, res_users.partner_id as partner_id, hr_leave.out_of_office_message as out_of_office_message, hr_leave.date_to as date_to, hr_leave.date_from as date_from
                                FROM res_users
                                JOIN hr_leave ON hr_leave.user_id = res_users.id
                                AND hr_leave.state not in ('cancel', 'refuse')
                                AND res_users.active = 't'
                                AND hr_leave.date_to >= %s
                                AND res_users.partner_id in %s ORDER BY date_to asc''', (now, tuple(partners_on_leave)))
            out_of_office_infos = {}
            for res in self.env.cr.dictfetchall():
                if out_of_office_infos.get(res['partner_id']):
                    out_of_office_infos[res['partner_id']].append(res)
                else:
                    out_of_office_infos[res['partner_id']] = [res]
            for partner_id, out_of_office_info in out_of_office_infos.items():
                first_leave = out_of_office_info[0]
                partner_infos[partner_id]['out_of_office_message'] = first_leave['out_of_office_message']
                partner_infos[partner_id]['out_of_office_date_end'] = first_leave['date_to']
                if first_leave.get('employee_id'):
                    employee_id = self.env['hr.employee'].browse(first_leave.get('employee_id'))
                    resource_calendar_id = employee_id.resource_calendar_id
                    working_days = resource_calendar_id.mapped('attendance_ids.dayofweek')
                    days = 1
                    for next_leave in out_of_office_info:
                        while str((first_leave['date_to'].date() + timedelta(days=days)).weekday()) not in working_days:
                            days += 1
                        if next_leave['date_from'].date() == first_leave['date_to'].date() + timedelta(days=days):
                            days = 1
                            partner_infos[partner_id]['out_of_office_date_end'] = next_leave['date_to']
                            first_leave = next_leave

        return partner_infos
