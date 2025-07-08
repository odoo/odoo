# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.tools import format_date
from odoo.addons.hr.models.res_users import field_employee
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    leave_date_to = field_employee(fields.Date, 'leave_date_to')
    on_public_leave = fields.Boolean(compute="_compute_on_public_leave")

    def _compute_on_public_leave(self):
        now = fields.Datetime.now()
        company_ids = self.mapped("company_id").ids
        if not company_ids:
            self.on_public_leave = False
            return
        domain = [
            ("resource_id", "=", False),
            ("company_id", "in", company_ids),
            ("date_from", "<=", now),
            ("date_to", ">=", now),
        ]
        grouped_companies = self.env["resource.calendar.leaves"]._read_group(domain, ["company_id"], ["__count"])
        companies_on_leave = {company.id for company, _ in grouped_companies if company}
        for user in self:
            user.on_public_leave = user.company_id.id in companies_on_leave

    def _compute_im_status(self):
        super()._compute_im_status()
        on_leave_user_ids = self._get_on_leave_ids()
        for user in self:
            if user.id in on_leave_user_ids:
                if user.im_status == 'online':
                    user.im_status = 'leave_online'
                elif user.im_status == 'away':
                    user.im_status = 'leave_away'
                elif user.im_status == 'busy':
                    user.im_status = 'leave_busy'
                elif user.im_status == 'offline':
                    user.im_status = 'leave_offline'

    @api.model
    def _get_on_leave_ids(self, partner=False):
        now = fields.Datetime.now()
        field = 'partner_id' if partner else 'id'
        self.flush_model(['active'])
        self.env['hr.leave'].flush_model(['user_id', 'state', 'date_from', 'date_to'])
        self.env["resource.calendar.leaves"].flush_model(["company_id", "date_from", "date_to"])
        self.env.cr.execute(f'''
            SELECT DISTINCT res_users.{field}
            FROM res_users
            WHERE res_users.active = TRUE AND (
                EXISTS (
                    SELECT 1 FROM hr_leave hl
                    JOIN hr_leave_type hlt ON hl.holiday_status_id = hlt.id
                    WHERE hl.user_id = res_users.id
                    AND hl.state = 'validate'
                    AND hlt.time_type = 'leave'
                    AND hl.date_from <= %s
                    AND hl.date_to >= %s
                )
                OR EXISTS (
                    SELECT 1 FROM resource_calendar_leaves rcl
                    WHERE rcl.resource_id IS NULL
                    AND rcl.company_id = res_users.company_id
                    AND rcl.date_from <= %s
                    AND rcl.date_to >= %s
                )
            )
        ''', (now, now, now, now))

        return [r[0] for r in self.env.cr.fetchall()]

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

    @api.depends("leave_date_to", "on_public_leave")
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        for user in self:
            if not user.env.context.get("formatted_display_name"):
                continue
            if user.leave_date_to:
                back_on = format_date(self.env, user.leave_date_to, self.env.user.lang, "medium")
                name = "%s \t ✈ --%s %s--" % (user.display_name or user.name, _("Back on"), back_on)
                user.display_name = name.strip()
            elif user.on_public_leave:
                name = "%s \t ✈ --%s--" % (user.display_name or user.name, _("Out of office due to public holiday"))
                user.display_name = name.strip()

    def _store_main_user_fields(self, res: Store.FieldList):
        super()._store_main_user_fields(res)
        if res.is_for_internal_users():
            res.attr("on_public_leave", predicate=lambda user: user.on_public_leave)
            res.many("employee_ids", ["leave_date_to"])
