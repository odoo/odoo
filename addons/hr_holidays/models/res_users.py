# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command
from odoo.tools import format_date, format_time
from odoo.addons.hr.models.res_users import related_employee_field
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    leave_back_datetime = fields.Datetime(**related_employee_field('leave_back_datetime'))
    leave_date_to = fields.Date(**related_employee_field('leave_date_to'))

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

    @api.depends('leave_back_datetime')
    @api.depends_context('formatted_display_name', 'tz')
    def _compute_display_name(self):
        super()._compute_display_name()
        for user in self:
            if user.env.context.get("formatted_display_name") and user.leave_back_datetime:
                back_at = fields.Datetime.context_timestamp(user, user.leave_back_datetime)
                if back_at.date() == fields.Date.context_today(user):
                    name = self.env._("%(name)s !!✈ Back at %(time)s!!",
                        name=user.display_name or user.name,
                        time=format_time(self.env, back_at.time(), time_format="short", lang_code=self.env.user.lang),
                    )
                else:
                    name = self.env._("%(name)s !!✈ Back on %(date)s!!",
                        name=user.display_name or user.name,
                        date=format_date(self.env, back_at.date(), self.env.user.lang, "medium"),
                    )
                user.display_name = name.strip()

    def _store_main_user_fields(self, res: Store.FieldList):
        super()._store_main_user_fields(res)
        res.many(
            "all_employee_ids",
            lambda res: (
                res.extend(["active", "company_id", "user_id"]),
                res.attr("leave_back_datetime", version=False),
                res.attr("leave_date_to", version=False),
            ),
            internal=True,
        )
