# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.tools import format_date
from odoo.addons.hr.models.res_users import field_employee
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    leave_date_to = field_employee(fields.Date, 'leave_date_to')

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

    @api.depends('leave_date_to')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        for user in self:
            if user.env.context.get("formatted_display_name") and user.leave_date_to:
                name = "%s \t ✈ --%s %s--" % (user.display_name or user.name, _("Back on"), format_date(self.env, user.leave_date_to, self.env.user.lang, "medium"))
                user.display_name = name.strip()

    def _store_main_user_fields(self, res: Store.FieldList):
        super()._store_main_user_fields(res)
        if res.is_for_internal_users():
            res.many("employee_ids", [
                "leave_date_to",
                "leave_date_from",
                "request_date_from_period",
                "next_working_day_on_leave",
            ])
