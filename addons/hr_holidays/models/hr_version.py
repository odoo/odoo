from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class HrVersion(models.Model):
    _inherit = "hr.version"
    _description = "Employee Contract"

    @api.constrains("contract_date_start", "contract_date_end")
    def _check_contracts(self):
        self._get_leaves()._check_contracts()

    @api.model_create_multi
    def create(self, vals_list):
        all_new_leave_origin = []
        all_new_leave_vals = []
        leaves_state = {}
        created_versions = self.env["hr.version"]
        for vals in vals_list:
            if "employee_id" not in vals or "resource_calendar_id" not in vals:
                created_versions |= super().create(vals)
                continue
            leaves = self._get_leaves_from_vals(vals)
            contract_date_start = fields.Date.to_date(
                vals.get("contract_date_start")
                or vals.get("date_version")
                or fields.Date.today()
            )
            is_created = False
            for leave in leaves:
                leaves_state = (
                    self._refuse_leave(leave, leaves_state)
                    if leave.request_date_from < contract_date_start
                    else self._set_leave_draft(leave, leaves_state)
                )
                if not is_created:
                    created_versions |= super().create([vals])
                    is_created = True
                overlapping_contracts = self._check_overlapping_contract(leave)
                if not overlapping_contracts:
                    leave._compute_date_from_to()
                    continue
                all_new_leave_origin, all_new_leave_vals = (
                    self._update_all_new_leave_vals_from_split_leave(
                        all_new_leave_origin,
                        all_new_leave_vals,
                        overlapping_contracts,
                        leave,
                        leaves_state,
                    )
                )
            if not is_created:
                created_versions |= super().create([vals])
        try:
            if all_new_leave_vals:
                self._create_all_new_leave(all_new_leave_origin, all_new_leave_vals)
        except ValidationError as e:
            raise ValidationError(
                self.env._(
                    "Changing the contract on this employee changes their working schedule in a period "
                    "they already took leaves. Changing this working schedule changes the duration of "
                    "these leaves in such a way the employee no longer has the required allocation for "
                    "them. Please review these leaves and/or allocations before changing the contract."
                )
            ) from e
        return created_versions

    def write(self, vals):
        written_contracts = self.env["hr.version"]
        if any(
            field in vals
            for field in [
                "contract_date_start",
                "contract_date_end",
                "date_version",
                "resource_calendar_id",
            ]
        ):
            all_new_leave_origin = []
            all_new_leave_vals = []
            leaves_state = {}
            try:
                for contract in self:
                    resource_calendar_id = vals.get(
                        "resource_calendar_id", contract.resource_calendar_id.id
                    )
                    extra_domain = (
                        [("resource_calendar_id", "!=", resource_calendar_id)]
                        if resource_calendar_id
                        else None
                    )
                    leaves = contract._get_leaves(extra_domain=extra_domain)
                    if not leaves:
                        continue
                    super(HrVersion, contract).write(vals)
                    written_contracts |= contract
                    for leave in leaves:
                        overlapping_contracts = self._check_overlapping_contract(leave)
                        if not overlapping_contracts:
                            continue
                        leaves_state = self._refuse_leave(leave, leaves_state)
                        all_new_leave_origin, all_new_leave_vals = (
                            self._update_all_new_leave_vals_from_split_leave(
                                all_new_leave_origin,
                                all_new_leave_vals,
                                overlapping_contracts,
                                leave,
                                leaves_state,
                            )
                        )
                if all_new_leave_vals:
                    self._create_all_new_leave(all_new_leave_origin, all_new_leave_vals)
            except ValidationError as e:
                raise ValidationError(
                    self.env._(
                        "Changing the contract on this employee changes their working schedule in a period "
                        "they already took leaves. Changing this working schedule changes the duration of "
                        "these leaves in such a way the employee no longer has the required allocation for "
                        "them. Please review these leaves and/or allocations before changing the contract."
                    )
                ) from e
        return super(HrVersion, self - written_contracts).write(vals)

    def _get_leaves(self, extra_domain=None):
        contracted = self.sudo().filtered("contract_date_start")
        if not contracted:
            return self.env["hr.leave"]
        domain = [
            ("state", "!=", "refuse"),
            ("employee_id", "in", contracted.employee_id.ids),
            (
                "date_from",
                "<=",
                max(end or date.max for end in contracted.mapped("contract_date_end")),
            ),
            ("date_to", ">=", min(contracted.mapped("contract_date_start"))),
        ]
        if extra_domain:
            domain = Domain.AND([domain, extra_domain])
        return self.env["hr.leave"].search(domain)

    def _get_leaves_from_vals(self, vals):
        domain = Domain(
            [
                ("state", "!=", "refuse"),
                ("employee_id", "=", vals["employee_id"]),
                (
                    "date_to",
                    ">=",
                    fields.Date.to_date(
                        vals.get("contract_date_start")
                        or vals.get("date_version")
                        or fields.Date.today()
                    ),
                ),
                ("resource_calendar_id", "!=", vals.get("resource_calendar_id")),
            ]
        )
        if vals.get("contract_date_end"):
            domain &= Domain(
                "date_from", "<=", fields.Date.to_date(vals["contract_date_end"])
            )
        return self.env["hr.leave"].search(domain)

    def _check_overlapping_contract(self, leave):
        overlapping_contracts = leave._get_overlapping_contracts().sorted(
            key=lambda c: c.contract_date_start
        )
        if len(overlapping_contracts.resource_calendar_id) <= 1:
            if overlapping_contracts:
                first_overlapping_contract = next(
                    iter(overlapping_contracts), overlapping_contracts
                )
                if (
                    leave.resource_calendar_id
                    != first_overlapping_contract.resource_calendar_id
                ):
                    leave.resource_calendar_id = (
                        first_overlapping_contract.resource_calendar_id
                    )
                    if not leave.request_unit_hours:
                        leave.with_context(
                            leave_skip_date_check=True, leave_skip_state_check=True
                        )._compute_date_from_to()
                        if leave.state == "validate":
                            leave._apply_leave_request()
            return False
        return overlapping_contracts

    def _refuse_leave(self, leave, leaves_state):
        if leave.id not in leaves_state:
            leaves_state[leave.id] = leave.state
        if leave.state not in ["refuse", "confirm"]:
            leave.action_refuse()
        return leaves_state

    def _set_leave_draft(self, leave, leaves_state):
        if leave.id not in leaves_state:
            leaves_state[leave.id] = leave.state
        if leave.state not in ["refuse", "confirm"]:
            leave.action_back_to_approval()
        return leaves_state

    def _update_all_new_leave_vals_from_split_leave(
        self,
        all_new_leave_origin,
        all_new_leave_vals,
        overlapping_contracts,
        leave,
        leaves_state,
    ):
        last_version = overlapping_contracts[-1]
        for overlapping_contract in overlapping_contracts:
            new_request_date_from = max(
                leave.request_date_from, overlapping_contract.contract_date_start
            )
            new_request_date_to = min(
                leave.request_date_to,
                overlapping_contract.contract_date_end or date.max,
            )
            new_leave_vals = leave.copy_data(
                {
                    "request_date_from": new_request_date_from,
                    "request_date_to": new_request_date_to,
                    "state": leaves_state[leave.id]
                    if overlapping_contract.id != last_version.id
                    else "confirm",
                }
            )[0]
            new_leave = self.env["hr.leave"].new(new_leave_vals)
            new_leave._compute_date_from_to()
            if new_leave.date_from < new_leave.date_to:
                all_new_leave_origin.append(leave)
                all_new_leave_vals.append(new_leave_vals)
        return all_new_leave_origin, all_new_leave_vals

    def _create_all_new_leave(self, all_new_leave_origin, all_new_leave_vals):
        new_leaves = (
            self.env["hr.leave"]
            .with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                leave_skip_state_check=True,
            )
            .create(all_new_leave_vals)
        )
        new_leaves.filtered(lambda l: l.state == "validate")._apply_leave_request()
        for index, new_leave in enumerate(new_leaves):
            new_leave.message_post_with_source(
                "mail.message_origin_link",
                render_values={
                    "self": new_leave,
                    "origin": all_new_leave_origin[index],
                },
                subtype_xmlid="mail.mt_note",
            )
