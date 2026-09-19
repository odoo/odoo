from collections import Counter

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import debug_log as dbg


class HrEmployeeChangeRequest(models.Model):
    _name = "hr.employee.change.request"
    _inherit = ["mixin.mail.thread", "mixin.approval"]
    _description = "Employee Personal Information Change Request"
    _order = "create_date desc, id desc"
    _rec_name = "employee_id"

    _PROPOSED_FIELDS = (
        "private_street",
        "private_street2",
        "private_city",
        "private_state_id",
        "private_zip",
        "private_country_id",
        "private_email",
        "private_phone_ids",
        "emergency_contact",
        "emergency_phone_ids",
    )

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        default=lambda self: self.env.user.employee_id,
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="employee_id.company_id",
    )
    requested_by_uid = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )

    private_street = fields.Char()
    private_street2 = fields.Char()
    private_city = fields.Char()
    private_state_id = fields.Many2one(comodel_name="res.country.state")
    private_zip = fields.Char()
    private_country_id = fields.Many2one(comodel_name="res.country")
    private_email = fields.Char()
    private_phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="hr_change_request_private_phone_rel",
    )
    emergency_contact = fields.Char()
    emergency_phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="hr_change_request_emergency_phone_rel",
    )

    # A partial unique index would say this in SQL, but EXCLUDE needs
    # btree_gist and this template does not carry it.
    @api.constrains("employee_id", "approval_state")
    def _check_one_pending_request_per_employee(self):
        pending = self.filtered(lambda request: request._is_awaiting_decision())
        if not pending:
            return
        # One query for the batch, and count the batch itself too: two pending
        # requests created together for one employee clash with each other and
        # neither is in the database yet to be found by the other.
        counts = Counter(pending.employee_id.ids)
        already = self.sudo().search(
            [
                ("employee_id", "in", pending.employee_id.ids),
                ("approval_state", "in", self._AWAITING_APPROVAL_STATES),
                ("id", "not in", pending.ids),
            ]
        )
        counts.update(already.employee_id.ids)
        clashing = [employee_id for employee_id, seen in counts.items() if seen > 1]
        dbg.logic.debug(
            "change request pending check on %s: %s already pending, clashing "
            "employees %s",
            dbg.rec(pending),
            dbg.rec(already),
            clashing,
        )
        if clashing:
            raise ValidationError(
                self.env._(
                    "%(employee)s already has a change request awaiting review.",
                    employee=self.env["hr.employee"]
                    .sudo()
                    .browse(clashing[0])
                    .display_name,
                )
            )

    _AWAITING_APPROVAL_STATES = ("new", "pending")

    def _is_awaiting_decision(self):
        self.check_singleton()
        return self.approval_state in self._AWAITING_APPROVAL_STATES

    def _proposed_values(self):
        """The fields this request actually changes, as employee write values."""
        self.check_singleton()
        values = {}
        for fname in self._PROPOSED_FIELDS:
            field = self._fields[fname]
            proposed = self[fname]
            current = self.employee_id.sudo()[fname]
            if field.type == "many2many":
                if set(proposed.ids) != set(current.ids):
                    values[fname] = [Command.set(proposed.ids)]
            elif field.type == "many2one":
                if proposed.id != current.id:
                    values[fname] = proposed.id
            elif proposed != current:
                values[fname] = proposed
        dbg.logic.debug(
            "[change_request:%s] proposes %s for employee %s",
            self.id,
            dbg.keys(values),
            self.employee_id.id,
        )
        return values

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        # Asking IS submitting: there is no draft a person would edit twice, so
        # the record raises and confirms its approval in the same breath the
        # hand-written workflow used to reach `pending` in.
        for request in requests:
            request.action_create_approval_request()
        return requests

    def _get_domain_approval_category(self):
        category = self.env.ref(
            "hr.approval_category_employee_change_request", raise_if_not_found=False
        )
        return [("id", "=", category.id)] if category else []

    def _get_fields_approval_protected(self):
        """What the reviewer is deciding on. The requester may not change it
        after asking: an approval would otherwise apply values nobody reviewed."""
        return ["employee_id", *self._PROPOSED_FIELDS]

    def _on_approval_approved(self):
        super()._on_approval_approved()
        for request in self:
            values = request._proposed_values()
            if values:
                dbg.pipeline.debug(
                    "[change_request:%s] approved by %s -> employee %s write %s",
                    request.id,
                    self.env.uid,
                    request.employee_id.id,
                    dbg.keys(values),
                )
                request.employee_id.sudo().write(values)

    @api.model
    def action_open_my_request(self):
        """Open the caller's pending request, seeded from what they hold today."""
        employee = self.env.user.employee_id
        if not employee:
            raise UserError(
                self.env._("You have no employee record to raise a request about.")
            )
        request = self.search(
            [
                ("employee_id", "=", employee.id),
                ("approval_state", "in", self._AWAITING_APPROVAL_STATES),
            ],
            limit=1,
        )
        dbg.logic.debug(
            "[employee:%s] action_open_my_request: %s",
            employee.id,
            dbg.lazy(
                lambda: (
                    f"pending request {request.id}" if request else "seeding a new one"
                )
            ),
        )
        if not request:
            seed = {"employee_id": employee.id}
            for fname in self._PROPOSED_FIELDS:
                value = employee.sudo()[fname]
                seed[fname] = (
                    [Command.set(value.ids)]
                    if self._fields[fname].type == "many2many"
                    else value.id
                    if self._fields[fname].type == "many2one"
                    else value
                )
            request = self.create(seed)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": request.id,
            "view_mode": "form",
            "target": "new",
            "name": self.env._("Request a change to my information"),
        }
