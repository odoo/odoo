# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC

from odoo import api, fields, models, Command
from odoo.tools import format_date, format_time
from odoo.addons.hr.models.res_users import related_employee_field
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    leave_date_to = fields.Date(**related_employee_field('leave_date_to'))
    leave_datetime_to = fields.Datetime(**related_employee_field('leave_datetime_to'))

    def _clean_leave_responsible_users(self):
        # self = old bunch of leave responsibles
        # This method compares the current leave managers
        # and remove the access rights to those who don't
        # need them anymore
        approver_group = 'hr_holidays.group_hr_holidays_responsible'
        if not any(u.has_group(approver_group) for u in self):
            return

        res = self.env['hr.employee']._read_group(
            [('leave_manager_id', 'in', self.ids)],
            ['leave_manager_id'])
        responsibles_to_remove_ids = set(self.ids) - {leave_manager.id for [leave_manager] in res}
        if responsibles_to_remove_ids:
            self.browse(responsibles_to_remove_ids).write({
                'group_ids': [Command.unlink(self.env.ref(approver_group).id)],
            })

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users.sudo()._clean_leave_responsible_users()
        return users

    @api.depends('leave_datetime_to')
    @api.depends_context('formatted_display_name', 'tz')
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get("formatted_display_name"):
            return
        today = fields.Date.context_today(self)
        for user in self:
            if not user.leave_datetime_to:
                continue
            # The day is the one of the viewer, unlike `leave_date_to` which is in UTC.
            back_on = user.leave_datetime_to.replace(tzinfo=UTC).astimezone(self.env.tz)
            if back_on.date() == today:
                name = self.env._("%(name)s !!✈ Back at %(time)s!!",
                    name=user.display_name or user.name,
                    time=format_time(self.env, back_on.time(), time_format="short"),
                )
            else:
                name = self.env._("%(name)s !!✈ Back on %(date)s!!",
                    name=user.display_name or user.name,
                    date=format_date(self.env, back_on.date(), self.env.user.lang, "medium"),
                )
            user.display_name = name.strip()

    def _store_main_user_fields(self, res: Store.FieldList):
        super()._store_main_user_fields(res)
        res.many(
            "all_employee_ids",
            ["active", "company_id", "leave_datetime_to", "user_id"],
            internal=True,
        )
