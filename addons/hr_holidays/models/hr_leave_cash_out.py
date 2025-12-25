from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class HrLeaveCashOut(models.Model):
    _name = "hr.leave.cash.out"
    _description = "Time Off Cash-out"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]
    _mail_post_access = "read"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        index=True,
        ondelete="restrict",
        required=True,
        tracking=True,
        domain=lambda self: self._get_employee_domain(),
        default=lambda self: self.env.user.employee_id,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        related="employee_id.user_id",
    )
    leave_type_id = fields.Many2one(
        "hr.leave.type",
        compute='_compute_leave_type_id',
        string="Time Off Type",
        required=True,
        store=True,
        domain="""[
            ('requires_allocation', '=', True),
            ('has_valid_allocation', '=', True),
        ]""",
        tracking=True,
    )
    leave_allocation_id = fields.Many2one(
        "hr.leave.allocation",
        domain="""
            [('employee_id', '=', employee_id), ('state', '=', 'validate'), ('holiday_status_id', '=', leave_type_id)]""",
        tracking=True,
        string="Allocation",
        required=True,
    )
    state = fields.Selection(
        [
            ("confirm", "To Approve"),
            ("refuse", "Refused"),
            ("validate1", "Second Approval"),
            ("validate", "Approved"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        store=True,
        tracking=True,
        copy=False,
        readonly=False,
        default="confirm",
    )
    request_unit = fields.Selection(related="leave_type_id.request_unit")
    quantity = fields.Float(string="Quantity")
    company_id = fields.Many2one(
        related="employee_id.company_id",
        string="Employee Company",
    )
    validation_type = fields.Selection(
        string="Validation Type",
        related="leave_type_id.leave_validation_type",
    )
    first_approver_id = fields.Many2one(
        "hr.employee",
        string="First Approval",
        readonly=True,
        copy=False,
        help="This area is automatically filled by the user who validate the time off",
    )
    second_approver_id = fields.Many2one(
        "hr.employee",
        string="Second Approval",
        readonly=True,
        copy=False,
        help="This area is automatically filled by the user who validate the time off with second level (If time off type need second validation)",
    )
    can_approve = fields.Boolean(
        "Can Approve", compute="_compute_can_approve", export_string_translation=False,
    )
    can_cancel = fields.Boolean(
        "Can Cancel", compute="_compute_can_cancel", export_string_translation=False,
    )
    can_validate = fields.Boolean(
        compute="_compute_can_validate", export_string_translation=False,
    )
    can_refuse = fields.Boolean(
        compute="_compute_can_refuse", export_string_translation=False,
    )
    can_back_to_approve = fields.Boolean(
        compute="_compute_can_back_to_approve", export_string_translation=False,
    )

    _quantity_check = models.Constraint(
        "CHECK ( quantity > 0 )",
        "The quantity must be greater than zero.",
    )

    @api.constrains('leave_type_id')
    def _check_leave_type_id_constraints(self):
        is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        for record in self:
            if not record.leave_type_id.allow_cash_out_request:
                msg = "The selected leave type does not allow cash out requests."
                raise ValidationError(msg)

            if not record.leave_type_id.requires_allocation:
                msg = "The selected leave type should require allocation."
                raise ValidationError(msg)

            if not record.leave_type_id.allow_employee_request and not is_officer:
                msg = "Only an officer or an administrator can create a cash out request of this time off type."
                raise ValidationError(msg)

    @api.depends("leave_type_id", "employee_id", "quantity")
    def _compute_display_name(self):
        for cash_out in self:
            unit = self.env._("hours") if cash_out.request_unit == 'hour' else self.env._("days")
            cash_out.display_name = self.env._(
                "%(person)s on %(leave_type)s: %(quantity)s %(unit)s",
                person=cash_out.employee_id.name or '',
                leave_type=cash_out.leave_type_id.name or '',
                quantity=cash_out.quantity,
                unit=unit,
            )

    @api.depends("employee_id")
    def _compute_leave_type_id(self):
        for cash_out in self:
            if cash_out._origin.employee_id == cash_out.employee_id:
                continue
            cash_out.leave_type_id = False
            cash_out.leave_allocation_id = False

    @api.depends("state", "employee_id")
    def _compute_can_approve(self):
        for cash_out in self:
            cash_out.can_approve = cash_out._check_approval_update(
                "validate1", raise_if_not_possible=False,
            )

    @api.depends("state", "employee_id")
    def _compute_can_validate(self):
        for cash_out in self:
            cash_out.can_validate = cash_out._check_approval_update(
                "validate", raise_if_not_possible=False,
            )

    @api.depends("state", "employee_id")
    def _compute_can_refuse(self):
        for cash_out in self:
            cash_out.can_refuse = cash_out._check_approval_update(
                "refuse", raise_if_not_possible=False,
            )

    @api.depends_context("uid")
    @api.depends("state", "employee_id")
    def _compute_can_cancel(self):
        for cash_out in self:
            cash_out.can_cancel = cash_out._check_approval_update(
                "cancel", raise_if_not_possible=False,
            )

    @api.depends("state", "employee_id")
    def _compute_can_back_to_approve(self):
        for cash_out in self:
            cash_out.can_back_to_approve = (
                cash_out.state == "validate"
                and cash_out._check_approval_update(
                    "confirm", raise_if_not_possible=False
                )
            )

    def _get_employee_domain(self):
        domain = [
            ("company_id", "in", self.env.companies.ids),
        ]
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_user"):
            domain += [
                "|",
                ("user_id", "=", self.env.uid),
                ("leave_manager_id", "=", self.env.uid),
            ]
        return domain

    def _add_follower(self, employee_id):
        employee = self.env["hr.employee"].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    ####################################################
    # Business methods
    ####################################################

    def _get_next_states_by_state(self):
        self.ensure_one()
        state_result = {
            "confirm": set(),
            "validate1": set(),
            "validate": set(),
            "refuse": set(),
            "cancel": set(),
        }
        validation_type = self.validation_type

        user_employees = self.env.user.employee_ids
        is_own_leave = self.employee_id in user_employees

        is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        is_time_off_manager = self.employee_id.leave_manager_id == self.env.user

        if is_own_leave:
            state_result["validate1"].add("cancel")
            state_result["validate"].add("cancel")
            state_result["refuse"].add("cancel")

        if is_officer:
            if validation_type == "both":
                state_result["confirm"].add("validate1")
                state_result["refuse"].add("validate1")
                state_result["cancel"].add("validate1")
            state_result["confirm"].update({"validate", "refuse"})
            state_result["validate1"].update({"confirm", "validate", "refuse"})
            state_result["validate"].update({"confirm", "refuse"})
            state_result["refuse"].update({"confirm", "validate"})
            state_result["cancel"].update({"confirm", "validate", "refuse"})
        elif is_time_off_manager:
            if validation_type != "hr":
                state_result["confirm"].add("refuse")
                state_result["validate"].add("refuse")
            if validation_type == "both":
                state_result["confirm"].add("validate1")
                state_result["validate1"].add("refuse")
            elif validation_type == "manager":
                state_result["confirm"].add("validate")
                state_result["refuse"].add("validate")

        return state_result

    def _check_approval_update(self, state, raise_if_not_possible=True):
        """Check if target state is achievable."""
        if self.env.is_superuser():
            return True

        for cash_out in self:
            is_time_off_manager = cash_out.employee_id.leave_manager_id == self.env.user
            dict_all_possible_state = cash_out._get_next_states_by_state()
            validation_type = cash_out.validation_type
            error_message = ""
            # Standard Check
            if cash_out.state == state:
                error_message = self.env._("You can't do the same action twice.")
            elif state == "validate1" and validation_type != "both":
                error_message = self.env._(
                    "Not possible state. State Approve is only used for cash out needed 2 approvals",
                )
            elif cash_out.state == "cancel":
                error_message = self.env._("A cancelled cash out cannot be modified.")

            elif state not in dict_all_possible_state.get(cash_out.state, {}):
                if state == "cancel":
                    error_message = self.env._(
                        "You can only cancel your own cash out. You can cancel a cash out only if this cash out \
is approved, validated or refused.",
                    )
                elif state == "confirm":
                    error_message = self.env._(
                        "You can't reset a cash out. Cancel/delete this one and create an other",
                    )
                elif state == "validate1":
                    if not is_time_off_manager:
                        error_message = self.env._(
                            "Only a Time Off Officer/Manager can approve a cash out.",
                        )
                    else:
                        error_message = self.env._(
                            "You can't approve a validated cash out.",
                        )
                elif state == "validate":
                    if not is_time_off_manager:
                        error_message = self.env._(
                            "Only a Time Off Officer/Manager can validate a cash out.",
                        )
                    elif cash_out.state == "refuse":
                        error_message = self.env._(
                            "You can't approve this refused cash out.",
                        )
                    else:
                        error_message = self.env._(
                            "You can only validate a cash out with validation by Time Off Manager.",
                        )
                elif state == "refuse":
                    if not is_time_off_manager:
                        error_message = self.env._(
                            "Only a Time Off Officer/Manager can refuse a cash out.",
                        )
                    else:
                        error_message = self.env._(
                            "You can't refuse a cash out with validation by Time Off Officer.",
                        )
            elif state != "cancel":
                try:
                    cash_out.check_access("write")
                except UserError as e:
                    if raise_if_not_possible:
                        raise UserError(e)
                    return False
                else:
                    continue
            if error_message:
                if raise_if_not_possible:
                    raise UserError(error_message)
                return False
        return True

    def action_approve(self, check_state=True):
        current_employee = self.env.user.employee_id
        cash_outs_to_approve = self.env["hr.leave.cash.out"]
        cash_outs_to_validate = self.env["hr.leave.cash.out"]
        for cash_out in self:
            if (check_state and cash_out.can_validate) or (
                not check_state and cash_out.validation_type != "both"
            ):
                cash_outs_to_validate += cash_out
            elif (check_state and cash_out.can_approve) or (
                not check_state and cash_out.validation_type == "both"
            ):
                cash_outs_to_approve += cash_out
            else:
                raise UserError(self.env._("You cannot approve this cash out."))
        cash_outs_to_approve.write(
            {"state": "validate1", "first_approver_id": current_employee.id},
        )
        cash_outs_to_validate._action_validate(check_state)
        self.activity_update()
        return True

    def _action_validate(self, check_state=True):
        current_employee = self.env.user.employee_id
        if check_state and any(not cash_out.can_validate for cash_out in self):
            raise UserError(self.env._("You can't validate this cash out."))

        self.write({"state": "validate"})

        cash_outs_second_approver = self.env["hr.leave.cash.out"]
        cash_outs_first_approver = self.env["hr.leave.cash.out"]

        for cash_out in self:
            if cash_out.validation_type == "both":
                cash_outs_second_approver += cash_out
            else:
                cash_outs_first_approver += cash_out

        cash_outs_second_approver.write({"second_approver_id": current_employee.id})
        cash_outs_first_approver.write({"first_approver_id": current_employee.id})

        return True

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(
            cash_out.state not in ["confirm", "validate", "validate1"]
            for cash_out in self
        ):
            raise UserError(
                self.env._(
                    "Cash-out request must be confirmed or validated in order to refuse it.",
                ),
            )

        self._notify_manager()
        validated_cash_outs = self.filtered(
            lambda cash_out: cash_out.state == "validate1",
        )
        validated_cash_outs.write(
            {"state": "refuse", "first_approver_id": current_employee.id},
        )
        (self - validated_cash_outs).write(
            {"state": "refuse", "second_approver_id": current_employee.id},
        )
        # Post a second message, more verbose than the tracking message
        for cash_out in self:
            if cash_out.employee_id.user_id:
                cash_out.message_post(
                    body=self.env._(
                        "Your cash-out for %(leave_type)s has been refused",
                        leave_type=cash_out.leave_type_id.display_name,
                    ),
                    partner_ids=cash_out.employee_id.user_id.partner_id.ids,
                )
        self.activity_update()
        return True

    def action_cancel(self):
        self.ensure_one()
        if not self.can_cancel:
            raise UserError(self.env._("This cash-out cannot be cancelled."))

        self.message_post(
            body=self.env._(
                "Your cash-out for %(leave_type)s has been cancelled.",
                leave_type=self.leave_type_id.display_name,
            ),
            subtype_xmlid="mail.mt_note",
        )
        self.sudo().state = "cancel"
        return True

    def action_back_to_approval(self):
        for cash_out in self:
            if not cash_out.can_back_to_approve:
                raise UserError(self.env._("This cash-out cannot be returned to approval."))
            cash_out.write({'state': 'confirm'})
            cash_out.activity_update()
        return True

    def _notify_manager(self):
        cash_outs = self.filtered(
            lambda cash_out: (
                cash_out.validation_type == "both"
                and cash_out.state in ["validate1", "validate"]
            )
            or (cash_out.validation_type == "manager" and cash_out.state == "validate"),
        )
        for cash_out in cash_outs:
            responsible = cash_out.employee_id.leave_manager_id.partner_id.ids
            if responsible:
                self.env["mail.thread"].sudo().message_notify(
                    partner_ids=responsible,
                    model_description="Leave Cash-out",
                    subject=self.env._("Refused Leave Cash-out"),
                    body=self.env._(
                        "%(cash_out_name)s has been refused.",
                        cash_out_name=cash_out.display_name,
                    ),
                    email_layout_xmlid="mail.mail_notification_light",
                )
        return True

    ####################################################
    # ORM Overrides methods
    ####################################################

    @api.model_create_multi
    def create(self, vals_list):
        leave_types = self.env["hr.leave.type"].browse(
            [
                values.get("leave_type_id")
                for values in vals_list
                if values.get("leave_type_id")
            ],
        )
        mapped_validation_type = {
            leave_type.id: leave_type.leave_validation_type
            for leave_type in leave_types
        }

        for values in vals_list:
            employee_id = values.get("employee_id", False)
            leave_type_id = values.get("leave_type_id")

            # Handle double validation
            if mapped_validation_type[leave_type_id] == "both":
                self._check_double_validation_rules(
                    employee_id, values.get("state", False),
                )

        cash_outs = super(
            HrLeaveCashOut, self.with_context(mail_create_nosubscribe=True),
        ).create(vals_list)
        cash_outs._check_validity()
        self.env["hr.leave.allocation"].invalidate_model(
            ["leaves_taken", "max_leaves"],
        )

        for cash_out in cash_outs:
            # Everything that is done here must be done using sudo because we might
            # have different create and write rights
            # eg : holidays_user can create a leave request with validation_type = 'manager' for someone else
            # but they can only write on it if they are leave_manager_id
            cash_out_sudo = cash_out.sudo()
            cash_out_sudo._add_follower(cash_out.employee_id.id)
            if cash_out.validation_type == "manager":
                cash_out.message_subscribe(
                    partner_ids=cash_out.employee_id.leave_manager_id.partner_id.ids,
                )
            if cash_out.validation_type == "no_validation":
                # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
                cash_out_sudo.action_approve()
                cash_out_sudo.message_subscribe(
                    partner_ids=cash_out._get_responsible_for_approval().partner_id.ids,
                )
                cash_out_sudo.message_post(
                    body=self.env._("The cash out has been automatically approved"),
                    subtype_xmlid="mail.mt_comment",
                )  # Message from OdooBot (sudo)
            else:
                cash_out_sudo.activity_update()
        return cash_outs

    def write(self, vals):
        is_officer = (
            self.env.user.has_group("hr_holidays.group_hr_holidays_user")
            or self.env.is_superuser()
        )
        if not is_officer and vals.keys():
            if any(leave.state == "cancel" for leave in self):
                raise UserError(self.env._("Only a manager can modify a canceled leave."))

        employee_id = vals.get("employee_id", False)
        if vals.get("state"):
            self._check_approval_update(vals["state"])
            if any(cash_out.validation_type == "both" for cash_out in self):
                if vals.get("employee_id"):
                    employees = self.env["hr.employee"].browse(
                        vals.get("employee_id"),
                    )
                else:
                    employees = self.mapped("employee_id")
                self._check_double_validation_rules(employees, vals["state"])
        result = super().write(vals)
        if any(
            field in vals
            for field in ["quantity", "leave_type_id", "employee_id", "state"]
        ):
            self._check_validity()
            self.env["hr.leave.allocation"].invalidate_model(
                ["leaves_taken", "max_leaves"],
            )  # missing dependency on compute
        for cash_out in self:
            if employee_id:
                cash_out._add_follower(employee_id)

        return result

    def _check_double_validation_rules(self, employees, state):
        if self.env.user.has_group("hr_holidays.group_hr_holidays_manager"):
            return

        is_leave_user = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        if state == "validate1":
            employees = employees.filtered(
                lambda employee: employee.leave_manager_id != self.env.user,
            )
            if employees and not is_leave_user:
                raise AccessError(
                    self.env._(
                        "You cannot first approve a cash-out for %s, because you are not his time off manager",
                        employees[0].name,
                    ),
                )
        elif state == "validate" and not is_leave_user:
            # Is probably handled via ir.rule
            raise AccessError(
                self.env._(
                    "You don't have the rights to apply second approval on a cash-out request",
                ),
            )

    def _check_validity(self):
        sorted_cash_outs = defaultdict(lambda: self.env["hr.leave.cash.out"])
        for cash_out in self:
            sorted_cash_outs[cash_out.leave_type_id] |= cash_out
        for leave_type, cash_outs in sorted_cash_outs.items():
            if not leave_type.requires_allocation:
                raise ValidationError(
                    self.env._("You must select a Time Off Type that requires allocation"),
                )
            employees = cash_outs.employee_id
            leave_data = leave_type.get_allocation_data(employees)

            previous_leave_data = leave_type.with_context(
                ignored_cash_out_ids=cash_outs.ids,
            ).get_allocation_data(employees)
            for employee in employees:
                previous_emp_data = (
                    previous_leave_data[employee]
                    and previous_leave_data[employee][0][1]["virtual_excess_data"]
                )
                emp_data = (
                    leave_data[employee]
                    and leave_data[employee][0][1]["virtual_excess_data"]
                )
                if not previous_emp_data and not emp_data:
                    continue
                previous_emp_data.setdefault("cash_out", 0)
                emp_data.setdefault("cash_out", 0)
                if previous_emp_data != emp_data and (
                    len(emp_data)
                    >= len(
                        previous_emp_data,
                    )
                    or emp_data["cash_out"] > previous_emp_data["cash_out"]
                ):
                    raise ValidationError(
                        self.env._("There is no valid allocation to cover that request."),
                    )

    ####################################################
    # Activity methods
    ####################################################

    def _get_responsible_for_approval(self):
        self.ensure_one()

        responsible = self.env["res.users"]
        if self.validation_type == "manager" or (
            self.validation_type == "both" and self.state == "confirm"
        ):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
            elif self.employee_id.parent_id.user_id:
                responsible = self.employee_id.parent_id.user_id
        elif self.validation_type == "hr" or (
            self.validation_type == "both" and self.state == "validate1"
        ):
            if self.leave_type_id.responsible_ids:
                responsible = self.leave_type_id.responsible_ids
        return responsible

    def _get_to_clean_activities(self):
        return ['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval']

    def activity_update(self):
        if self.env.context.get('mail_activity_automation_skip'):
            return False

        to_clean, to_do, to_do_confirm_activity = self.env['hr.leave.cash.out'], self.env['hr.leave.cash.out'], self.env['hr.leave.cash.out']
        activity_vals = []
        model_id = self.env.ref('hr_holidays.model_hr_leave_cash_out').id
        confirm_activity = self.env.ref('hr_holidays.mail_act_leave_approval')
        approval_activity = self.env.ref('hr_holidays.mail_act_leave_second_approval')
        for cash_out in self:
            if cash_out.state in ['confirm', 'validate1']:
                if cash_out.leave_type_id.leave_validation_type != 'no_validation':
                    if cash_out.state == 'confirm':
                        activity_type = confirm_activity
                        note = self.env._(
                            'New %(leave_type)s Cash Out Request created by %(user)s',
                            leave_type=cash_out.leave_type_id.name,
                            user=cash_out.create_uid.name,
                        )
                    else:
                        activity_type = approval_activity
                        note = self.env._(
                            'Second approval request for %(leave_type)s',
                            leave_type=cash_out.leave_type_id.name,
                        )
                        to_do_confirm_activity |= cash_out
                    user_ids = cash_out.sudo()._get_responsible_for_approval().ids
                    for user_id in user_ids:
                        activity_vals.append({
                            'activity_type_id': activity_type.id,
                            'automated': True,
                            'note': note,
                            'user_id': user_id,
                            'res_id': cash_out.id,
                            'res_model_id': model_id,
                        })
            elif cash_out.state == 'validate':
                to_do |= cash_out
            elif cash_out.state in ['refuse', 'cancel']:
                to_clean |= cash_out
        if to_clean:
            to_clean.activity_unlink(self._get_to_clean_activities(), only_automated=False)
        if to_do_confirm_activity:
            to_do_confirm_activity.activity_feedback(['hr_holidays.mail_act_leave_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
        self.env['mail.activity'].with_context(short_name=False).create(activity_vals)
        return None

    ####################################################
    # Messaging methods
    ####################################################

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if any(cash_out.state in ["validate", "validate1"] for cash_out in self):
            self.check_access("read")
            return super(HrLeaveCashOut, self.sudo()).message_subscribe(
                partner_ids=partner_ids, subtype_ids=subtype_ids,
            )
        return super().message_subscribe(
            partner_ids=partner_ids, subtype_ids=subtype_ids,
        )
