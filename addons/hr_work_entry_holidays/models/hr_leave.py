from datetime import date, datetime, time

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    work_entry_type_id = fields.Many2one(
        comodel_name="hr.work.entry.type",
        index="btree_not_null",
    )


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _prepare_resource_leave_vals(self):
        vals = super()._prepare_resource_leave_vals()
        vals["work_entry_type_id"] = self.holiday_status_id.work_entry_type_id.id
        return vals

    def _cancel_work_entry_conflict(self):
        if not self:
            return

        work_entries_vals_list = []
        for leave in self:
            contracts = leave.employee_id.sudo()._get_versions_with_contract_overlap_with_period(
                leave.date_from.date(), leave.date_to.date()
            )
            for contract in contracts:
                if (
                    leave.date_to >= contract.date_generated_from
                    and leave.date_from <= contract.date_generated_to
                ):
                    work_entries_vals_list += contract._prepare_work_entries_values(
                        datetime.combine(leave.date_from, time.min),
                        datetime.combine(leave.date_to, time.max),
                    )

        work_entries_vals_list = self.env[
            "hr.version"
        ]._generate_work_entries_postprocess(work_entries_vals_list)
        new_leave_work_entries = self.env["hr.work.entry"].create(
            work_entries_vals_list
        )
        _debug.pipeline(
            "leave_work_entries_generated",
            leaves=self,
            entries=new_leave_work_entries,
        )

        if new_leave_work_entries:
            start = min(self.mapped("date_from"), default=False)
            stop = max(self.mapped("date_to"), default=False)
            work_entry_groups = self.env["hr.work.entry"]._read_group(
                [
                    ("date", "<=", stop),
                    ("date", ">=", start),
                    ("employee_id", "in", self.employee_id.ids),
                ],
                ["employee_id"],
                ["id:recordset"],
            )
            work_entries_by_employee = {
                employee.id: work_entries
                for employee, work_entries in work_entry_groups
            }

            included = self.env["hr.work.entry"]
            overlappping = self.env["hr.work.entry"]
            for work_entries in work_entries_by_employee.values():
                new_employee_work_entries = work_entries & new_leave_work_entries
                previous_employee_work_entries = work_entries - new_leave_work_entries

                leave_intervals = new_employee_work_entries._to_intervals()
                conflicts_intervals = previous_employee_work_entries._to_intervals()

                outside_intervals = conflicts_intervals - leave_intervals

                overlappping |= self.env["hr.work.entry"]._from_intervals(
                    outside_intervals
                )
                included |= previous_employee_work_entries - overlappping
            overlappping.filtered(lambda entry: entry.state != "validated").write(
                {"leave_id": False}
            )
            included = included.filtered(lambda entry: entry.state != "validated")
            stale_leaves = (
                included.mapped("leave_id").filtered(
                    lambda l: l.state in ("confirm", "validate", "validate1")
                )
                - self
            )
            _debug.lifecycle(
                "conflicting_entries_archived",
                archived=included,
                unlinked_from_leave=overlappping,
                stale_leaves=stale_leaves,
            )
            included.write({"active": False})
            stale_leaves.action_refuse()

    def write(self, vals):
        if not self:
            return True
        skip_check = not bool(
            {"employee_id", "state", "request_date_from", "request_date_to"}
            & vals.keys()
        )
        employee_ids = self.employee_id.ids
        if vals.get("employee_id"):
            employee_ids += [vals["employee_id"]]
        start_dates = self.filtered("request_date_from").mapped("request_date_from") + [
            fields.Date.to_date(vals.get("request_date_from", False)) or date.max
        ]
        stop_dates = self.filtered("request_date_to").mapped("request_date_to") + [
            fields.Date.to_date(vals.get("request_date_to", False)) or date.min
        ]
        start = datetime.combine(min(start_dates) - relativedelta(days=1), time.min)
        stop = datetime.combine(max(stop_dates) + relativedelta(days=1), time.max)
        with self.env["hr.work.entry"]._error_checking(
            start=start, stop=stop, skip=skip_check, employee_ids=employee_ids
        ):
            return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        employee_ids = {v["employee_id"] for v in vals_list if v.get("employee_id")}
        start_dates = [
            fields.Date.to_date(v.get("request_date_from"))
            for v in vals_list
            if v.get("request_date_from")
        ]
        stop_dates = [
            fields.Date.to_date(v.get("request_date_to"))
            for v in vals_list
            if v.get("request_date_to")
        ]
        start = datetime.combine(
            min(start_dates, default=date.max) - relativedelta(days=1), time.min
        )
        stop = datetime.combine(
            max(stop_dates, default=date.min) + relativedelta(days=1), time.max
        )
        with self.env["hr.work.entry"]._error_checking(
            start=start, stop=stop, employee_ids=employee_ids
        ):
            return super().create(vals_list)

    def _filtered_on_public_holiday(self):
        return (
            super()
            ._filtered_on_public_holiday()
            .filtered(
                lambda l: (
                    l.holiday_status_id.work_entry_type_id.code
                    not in ["LEAVE110", "LEAVE210", "LEAVE280"]
                )
            )
        )

    def _apply_leave_request(self):
        super()._apply_leave_request()
        self.sudo()._cancel_work_entry_conflict()
        return True

    def action_refuse(self):
        res = super().action_refuse()
        self._regen_work_entries()
        return res

    def _move_validate_leave_to_confirm(self):
        res = super()._move_validate_leave_to_confirm()
        self._regen_work_entries()
        return res

    def _action_user_cancel(self, reason=None):
        res = super()._action_user_cancel(reason)
        self.sudo()._regen_work_entries()
        return res

    def _regen_work_entries(self):
        work_entries = (
            self.env["hr.work.entry"].sudo().search([("leave_id", "in", self.ids)])
        )

        _debug.pipeline("regen_work_entries", leaves=self, entries=work_entries)
        work_entries.write({"active": False})
        vals_list = []
        for work_entry in work_entries:
            vals_list += work_entry.version_id._prepare_work_entries_values(
                datetime.combine(work_entry.date, time.min),
                datetime.combine(work_entry.date, time.max),
            )
        vals_list = self.env["hr.version"]._generate_work_entries_postprocess(vals_list)
        self.env["hr.work.entry"].sudo().create(vals_list)

    def _compute_can_cancel(self):
        super()._compute_can_cancel()

        cancellable_leaves = self.filtered("can_cancel")
        work_entries = (
            self.env["hr.work.entry"]
            .sudo()
            .search(
                [
                    ("state", "=", "validated"),
                    ("leave_id", "in", cancellable_leaves.ids),
                ]
            )
        )
        leave_ids = work_entries.mapped("leave_id").ids

        _debug.logic(
            "can_cancel_blocked_by_validated",
            candidates=cancellable_leaves,
            blocked=len(leave_ids),
        )
        for leave in cancellable_leaves:
            leave.can_cancel = leave.id not in leave_ids
