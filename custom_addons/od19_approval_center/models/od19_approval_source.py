from odoo import fields, models


class Od19ApprovalSource(models.Model):
    _name = "od19.approval.source"
    _description = "Approval Center Source"
    _order = "sequence, id"

    OD19_MAX_RECORDS = 500

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade"
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Model Name")
    icon = fields.Char(default="fa-inbox")
    action_xmlid = fields.Char(string="Action XML ID")
    sequence = fields.Integer(default=10)
    requester_field = fields.Char(default="create_uid")
    requester_kind = fields.Selection(
        [("user", "User"), ("employee", "Employee")], default="user", required=True
    )
    submitted_date_field = fields.Char(default="create_date")
    decided_date_field = fields.Char()
    rejected_states = fields.Char(help="Comma separated state values meaning rejected.")
    success_states = fields.Char(help="Comma separated state values meaning success.")
    strategy = fields.Selection(
        [("field", "Field"), ("tier_validation", "Tier Validation")],
        default="field",
        required=True,
    )
    sla_days = fields.Integer(default=0, help="0 = no SLA warning.")
    active = fields.Boolean(default=True)
    step_ids = fields.One2many("od19.approval.step", "source_id", string="Steps")

    # ------------------------------------------------------------------
    # Low level helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _od19_csv(value):
        if not value:
            return []
        return [token.strip() for token in value.split(",") if token.strip()]

    def _od19_me_ids(self, kind):
        """Return the current user/employee/partner id for ``kind`` (0 if none)."""
        user = self.env.user
        if kind == "employee":
            return user.employee_id.id if "employee_id" in user._fields else 0
        if kind == "partner":
            return user.partner_id.id or 0
        return user.id or 0

    def _od19_ready(self):
        self.ensure_one()
        return bool(self.model_name) and self.model_name in self.env

    def _od19_main_state_field(self, steps):
        return steps[0].state_field or "state" if steps else "state"

    def _od19_field_ok(self, record, field_name):
        return bool(field_name) and field_name in record._fields

    def _od19_current_index(self, record, steps):
        """Index of the step the record waits at, or None."""
        for index, step in enumerate(steps):
            field_name = step.state_field or "state"
            if self._od19_field_ok(record, field_name) and record[field_name] == step.state_value:
                return index
        return None

    def _od19_index_of_my_step(self, record, steps):
        """Index of the first step where the current user is the approver, or None."""
        for index, step in enumerate(steps):
            if not self._od19_field_ok(record, step.approver_field):
                continue
            value = record[step.approver_field]
            if not value:
                continue
            comodel = record._fields[step.approver_field].comodel_name
            me_id = self._od19_me_ids_for_comodel(comodel, step.approver_kind)
            if me_id and value.id == me_id:
                return index
        return None

    def _od19_me_ids_for_comodel(self, comodel, kind):
        """Map the current user onto the comodel stored by the approver field."""
        user = self.env.user
        if comodel == "hr.employee":
            return user.employee_id.id if "employee_id" in user._fields else 0
        if comodel == "res.partner":
            return user.partner_id.id or 0
        if comodel == "res.users":
            return user.id or 0
        return self._od19_me_ids(kind)

    def _od19_classify_for_approver(self):
        """Return the 4 approver buckets for the current user (strategy=field)."""
        self.ensure_one()
        buckets = {"pending": [], "incoming": [], "done": [], "rejected": []}
        if not self._od19_ready():
            return buckets
        steps = self.step_ids.sorted("sequence")
        if not steps:
            return buckets
        Model = self.env[self.model_name].sudo()
        rejected = self._od19_csv(self.rejected_states)
        success = self._od19_csv(self.success_states)
        main_field = self._od19_main_state_field(steps)
        records = Model.search([], limit=self.OD19_MAX_RECORDS)
        for record in records:
            my_index = self._od19_index_of_my_step(record, steps)
            if my_index is None:
                continue
            state_value = record[main_field] if self._od19_field_ok(record, main_field) else False
            if state_value in rejected:
                buckets["rejected"].append(record)
                continue
            if state_value in success:
                buckets["done"].append(record)
                continue
            current = self._od19_current_index(record, steps)
            if current is None:
                continue
            if current == my_index:
                buckets["pending"].append(record)
            elif current < my_index:
                buckets["incoming"].append(record)
        return buckets
