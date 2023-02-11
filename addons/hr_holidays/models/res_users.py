# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class User(models.Model):
    _inherit = "res.users"

    leave_manager_id = fields.Many2one(related='employee_id.leave_manager_id')
    show_leaves = fields.Boolean(related='employee_id.show_leaves')
    allocation_used_count = fields.Float(related='employee_id.allocation_used_count')
    allocation_count = fields.Float(related='employee_id.allocation_count')
    leave_date_to = fields.Date(related='employee_id.leave_date_to')
    current_leave_state = fields.Selection(related='employee_id.current_leave_state')
    is_absent = fields.Boolean(related='employee_id.is_absent')
    allocation_used_display = fields.Char(related='employee_id.allocation_used_display')
    allocation_display = fields.Char(related='employee_id.allocation_display')
    hr_icon_display = fields.Selection(related='employee_id.hr_icon_display')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'leave_manager_id',
            'show_leaves',
            'allocation_used_count',
            'allocation_count',
            'leave_date_to',
            'current_leave_state',
            'is_absent',
            'allocation_used_display',
            'allocation_display',
            'hr_icon_display',
        ]

    def _compute_im_status(self):
        super(User, self)._compute_im_status()
        on_leave_user_ids = self._get_on_leave_ids()
        for user in self:
            if user.id in on_leave_user_ids:
                if user.im_status == 'online':
                    user.im_status = 'leave_online'
                elif user.im_status == 'away':
                    user.im_status = 'leave_away'
                else:
                    user.im_status = 'leave_offline'

    @api.model
    def _get_on_leave_ids(self, partner=False):
        now = fields.Datetime.now()
        field = 'partner_id' if partner else 'id'
        self.env['res.users'].flush(fnames=['active'])
        self.env['hr.leave'].flush(fnames=['user_id', 'state', 'date_from', 'date_to'])
        self.env.cr.execute('''SELECT res_users.%s FROM res_users
                            JOIN hr_leave ON hr_leave.user_id = res_users.id
                            AND state in ('validate')
                            AND res_users.active = 't'
                            AND date_from <= %%s AND date_to >= %%s''' % field, (now, now))
        return [r[0] for r in self.env.cr.fetchall()]

    def _clean_leave_responsible_users(self):
        # self = old bunch of leave responsibles
        # This method compares the current leave managers
        # and remove the access rights to those who don't
        # need them anymore
        approver_group = self.env.ref('hr_holidays.group_hr_holidays_responsible', raise_if_not_found=False)
        if not self or not approver_group:
            return
        res = self.env['hr.employee'].read_group(
            [('leave_manager_id', 'in', self.ids)],
            ['leave_manager_id'],
            ['leave_manager_id'])
        responsibles_to_remove_ids = set(self.ids) - {x['leave_manager_id'][0] for x in res}
        approver_group.sudo().write({
            'users': [(3, manager_id) for manager_id in responsibles_to_remove_ids]})
