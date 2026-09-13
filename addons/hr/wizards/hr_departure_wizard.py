from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class HrDepartureWizard(models.TransientModel):
    _name = "hr.departure.wizard"
    _description = "Departure Wizard"

    def _default_departure_date(self):
        if len(active_ids := self.env.context.get("active_ids", [])) == 1:
            employee = self.env["hr.employee"].browse(active_ids[0]).sudo()
            departure_date = employee and employee._get_departure_date()
        else:
            departure_date = False

        dbg.logic.debug(
            "hr.departure.wizard default date: active_ids=%s -> %s",
            active_ids,
            departure_date or "today",
        )
        return departure_date or fields.Date.today()

    def _default_employee_ids(self):
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            return (
                self.env["hr.employee"]
                .browse(active_ids)
                .filtered(lambda e: e.company_id in self.env.companies)
            )
        return self.env["hr.employee"]

    def _domain_employee_ids(self):
        return [("active", "=", True), ("company_id", "in", self.env.companies.ids)]

    departure_reason_id = fields.Many2one(
        comodel_name="hr.departure.reason",
        default=lambda self: self.env["hr.departure.reason"].search([], limit=1),
        required=True,
    )
    departure_description = fields.Html(string="Additional Information")
    departure_date = fields.Date(
        string="Contract End Date",
        default=_default_departure_date,
        required=True,
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        default=_default_employee_ids,
        required=True,
        domain=_domain_employee_ids,
        context={"active_test": False},
    )

    is_user_employee = fields.Boolean(
        string="User Employee",
        compute="_compute_is_user_employee",
    )
    remove_related_user = fields.Boolean(
        string="Related User",
        help="If checked, the related user will be removed from the system.",
    )

    set_date_end = fields.Boolean(
        string="Set Contract End Date",
        default=lambda self: self.env.user.has_group("hr.group_hr_manager"),
        help="Set the end date on the current contract.",
    )

    @api.depends("employee_ids.user_id")
    def _compute_is_user_employee(self):
        for wizard in self:
            wizard.is_user_employee = bool(wizard.employee_ids.user_id)

    def _prepare_action_user_archive_notification(
        self, message, message_type, next_action
    ):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("User Archive Notification"),
                "type": message_type,
                "message": message,
                "next": next_action,
            },
        }

    def _split_users_archivable_and_kept(self):
        archivable = kept = self.env["res.users"]
        if not self.remove_related_user:
            return archivable, kept
        employees_per_user = self.employee_ids.grouped("user_id")
        total_per_user = dict(
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            ._read_group(
                domain=[("user_id", "in", self.employee_ids.user_id.ids)],
                groupby=["user_id"],
                aggregates=["id:count"],
            )
        )
        for user, employees in employees_per_user.items():
            if not user:
                continue
            if len(employees) == total_per_user.get(user, 0):
                archivable |= user
            else:
                kept |= user
        dbg.logic.debug(
            "hr.departure.wizard %s: users archivable %s, kept (other employees) %s",
            self.id,
            dbg.rec(archivable),
            dbg.rec(kept),
        )
        return archivable, kept

    def _check_departure_date_against_contracts(self, versions):
        if any(
            version.contract_date_start
            and version.contract_date_start > self.departure_date
            for version in versions.sudo()
        ):
            raise UserError(
                self.env._(
                    "Departure date can't be earlier than the start date of current contract."
                )
            )

    @dbg.timed
    def action_register_departure(self):
        employee_ids = self.employee_ids
        active_versions = employee_ids.version_id
        dbg.lifecycle.debug(
            "[departure:%s] start: employees %s, date %s, reason %s, termination=%s "
            "remove_user=%s set_date_end=%s",
            self.id,
            dbg.rec(employee_ids),
            self.departure_date,
            self.departure_reason_id.id,
            bool(self.env.context.get("employee_termination")),
            self.remove_related_user,
            self.set_date_end,
        )
        self._check_departure_date_against_contracts(active_versions)

        allow_archived_users, unarchived_users = self._split_users_archivable_and_kept()

        archived_employees = self.env["hr.employee"]
        archived_users = self.env["res.users"]
        if self.env.context.get("employee_termination", False):
            archived_employees = employee_ids.filtered("active")
            if self.remove_related_user:
                archived_users = archived_employees.user_id & allow_archived_users

        dbg.pipeline.debug(
            "[departure:%s] archiving employees %s",
            self.id,
            dbg.rec(archived_employees),
        )
        archived_employees.with_context(no_wizard=True).action_archive()
        archived_users = archived_users.filtered(
            lambda u: u.id not in (self.env.uid, SUPERUSER_ID)
        )
        dbg.pipeline.debug(
            "[departure:%s] archiving users %s", self.id, dbg.rec(archived_users)
        )
        archived_users.sudo().action_archive()

        dbg.pipeline.debug(
            "[departure:%s] writing departure fields on %s",
            self.id,
            dbg.rec(employee_ids),
        )
        employee_ids.write(
            {
                "departure_reason_id": self.departure_reason_id,
                "departure_description": self.departure_description,
                "departure_date": self.departure_date,
            }
        )

        if self.set_date_end:
            contracts = active_versions.filtered(lambda v: v.contract_date_start)
            dbg.pipeline.debug(
                "[departure:%s] contract end %s on versions %s",
                self.id,
                self.departure_date,
                dbg.rec(contracts),
            )
            contracts.write({"contract_date_end": self.departure_date})

        next_action = {"type": "ir.actions.act_window_close"}
        for users, message_type, message in (
            (
                archived_users,
                "success",
                self.env._(
                    "The following users have been archived: %s",
                    ", ".join(archived_users.mapped("name")),
                ),
            ),
            (
                unarchived_users,
                "danger",
                self.env._(
                    "The following users have not been archived as they are still linked to another active employees: %s",
                    ", ".join(unarchived_users.mapped("name")),
                ),
            ),
        ):
            if users:
                next_action = self._prepare_action_user_archive_notification(
                    message, message_type, next_action
                )
        dbg.lifecycle.debug("[departure:%s] done", self.id)
        return next_action
