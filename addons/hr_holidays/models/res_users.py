# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command
from odoo.fields import Domain
from odoo.tools import format_date
from odoo.addons.hr.models.res_users import related_employee_field
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

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

    @api.depends('leave_date_to')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        for user in self:
            if user.env.context.get("formatted_display_name") and user.leave_date_to:
                name = self.env._("%(name)s !!✈ Back on %(date)s!!",
                    name=user.display_name or user.name,
                    date=format_date(self.env, user.leave_date_to, self.env.user.lang, "medium"),
                )
                user.display_name = name.strip()

    def _store_main_user_fields(self, res: Store.FieldList):
        super()._store_main_user_fields(res)
        res.many(
            "all_employee_ids", ["active", "company_id", "leave_date_to", "user_id"], internal=True,
        )

    @api.model
    def _add_im_status_changes(self, stores, since, until):
        super()._add_im_status_changes(stores, since, until)
        # sudo: hr.leave - im_status flags are sent to the internal presence channels
        leaves = (
            self.env["hr.leave"]
            .sudo()
            .search(
                self.env["hr.leave"]._get_absence_domain()
                & Domain("date_from", "<=", until)
                & Domain("date_to", ">=", since)
            )
        )
        absent_employee_ids = {since: set(), until: set()}
        for leave in leaves:
            for dt, employee_ids in absent_employee_ids.items():
                if leave.date_from <= dt <= leave.date_to:
                    employee_ids.add(leave.employee_id.id)
        changed = absent_employee_ids[since] ^ absent_employee_ids[until]
        # values read now, not when the store is serialized at commit
        for employee in leaves.employee_id.browse(changed).filtered("user_id"):
            stores[employee.user_id, "presence_internal"].add(
                employee,
                {
                    "is_absent": employee.id in absent_employee_ids[until],
                    "leave_date_to": employee.leave_date_to,
                },
            )

    @api.model
    def _send_is_absent(self, employees):
        """Send the current is_absent of ``employees``, for edits that change it right away:
        the cron compares both ends of its window on current data and cannot see them."""
        if not employees:
            return
        employees.invalidate_recordset(["is_absent", "leave_date_to"])
        stores = Store.Stores()
        for employee in employees.filtered("user_id"):
            stores[employee.user_id, "presence_internal"].add(
                employee,
                {"is_absent": employee.is_absent, "leave_date_to": employee.leave_date_to},
            )

    @api.model
    def _get_next_im_status_change(self, after):
        next_changes = [super()._get_next_im_status_change(after)]
        # sudo: hr.leave - im_status flags are sent to the internal presence channels
        leaves = self.env["hr.leave"].sudo()
        absence = leaves._get_absence_domain()
        for field, operator in [("date_from", ">"), ("date_to", ">=")]:
            leave = leaves.search(
                absence & Domain(field, operator, after), order=field, limit=1
            )
            next_changes.append(leave[field])
        return min(filter(None, next_changes), default=None)
