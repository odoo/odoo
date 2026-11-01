import datetime

from odoo import api, fields, models


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
        """Index of the furthest step the record has reached, or None.

        A record can match several steps at once (e.g. ``hr.expense`` keeps
        ``state='submitted'`` while ``second_approval_state='pending'``), so we
        return the highest matching index -- the real current step.
        """
        current = None
        for index, step in enumerate(steps):
            field_name = step.state_field or "state"
            if self._od19_field_ok(record, field_name) and record[field_name] == step.state_value:
                current = index
        return current

    def _od19_index_of_my_step(self, record, steps):
        """Index of the first step this user acts on, or None.

        A step with no ``approver_field`` is a shared pool step: it is the
        current user's step for every internal user (design D10).
        """
        for index, step in enumerate(steps):
            if not step.approver_field:
                return index
            if self._od19_is_approver_at(record, step):
                return index
        return None

    def _od19_is_approver_at(self, record, step):
        """True when the current user is the approver designated by this step."""
        if not self._od19_field_ok(record, step.approver_field):
            return False
        value = record[step.approver_field]
        if not value:
            return False
        comodel = record._fields[step.approver_field].comodel_name
        me_id = self._od19_me_ids_for_comodel(comodel, step.approver_kind)
        return bool(me_id) and value.id == me_id

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
            elif not steps[current].approver_field or self._od19_is_approver_at(record, steps[current]):
                buckets["pending"].append(record)
        return buckets

    def _od19_classify_for_requester(self):
        """Return the 4 requester buckets for the current user."""
        self.ensure_one()
        buckets = {"pending": [], "incoming": [], "done": [], "rejected": []}
        if not self._od19_ready():
            return buckets
        if not self._od19_field_ok(self.env[self.model_name], self.requester_field):
            return buckets
        me_id = self._od19_me_ids(self.requester_kind)
        if not me_id:
            return buckets
        steps = self.step_ids.sorted("sequence")
        rejected = self._od19_csv(self.rejected_states)
        success = self._od19_csv(self.success_states)
        main_field = self._od19_main_state_field(steps)
        records = self.env[self.model_name].sudo().search(
            [(self.requester_field, "=", me_id)], limit=self.OD19_MAX_RECORDS
        )
        for record in records:
            state_value = record[main_field] if self._od19_field_ok(record, main_field) else False
            if state_value in rejected:
                buckets["rejected"].append(record)
            elif state_value in success:
                buckets["done"].append(record)
            else:
                current = self._od19_current_index(record, steps)
                if current is not None and current > 0:
                    buckets["incoming"].append(record)
                else:
                    buckets["pending"].append(record)
        return buckets

    def _od19_age_days(self, record):
        """Whole days between the submitted date and now (0 if unknown)."""
        field_name = self.submitted_date_field or "create_date"
        if not self._od19_field_ok(record, field_name):
            field_name = "create_date"
        start = record[field_name]
        if not start:
            return 0
        if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
            start = datetime.datetime.combine(start, datetime.time.min)
        delta = fields.Datetime.now() - start
        return max(int(delta.total_seconds() // 86400), 0)

    def _od19_sla_state(self, age_days):
        if not self.sla_days:
            return "normal"
        if age_days >= 2 * self.sla_days:
            return "over"
        if age_days >= self.sla_days:
            return "warning"
        return "normal"

    # ------------------------------------------------------------------
    # Presentation layer (dict rows consumed by QWeb)
    # ------------------------------------------------------------------
    def _od19_record_label(self, record):
        for field_name in ("name", "display_name"):
            if self._od19_field_ok(record, field_name) and record[field_name]:
                return str(record[field_name])
        return "ID %s" % record.id

    def _od19_deep_link(self, record):
        return "/web#id=%s&model=%s&view_type=form" % (record.id, self.model_name)

    def _od19_build_rows(self, records):
        """Turn a recordset into plain dicts (safe to pass to QWeb)."""
        rows = []
        for record in records:
            age_days = self._od19_age_days(record)
            rows.append({
                "id": record.id,
                "source_name": self.name,
                "icon": self.icon or "fa-inbox",
                "model": self.model_name,
                "model_label": self.model_id.name,
                "label": self._od19_record_label(record),
                "url": self._od19_deep_link(record),
                "age_days": age_days,
                "sla_state": self._od19_sla_state(age_days),
            })
        return rows

    @api.model
    def _od19_summary(self, rows):
        """Aggregate KPI over a list of row dicts (approver *pending*)."""
        ages = [row["age_days"] for row in rows]
        return {
            "pending_count": len(rows),
            "max_age_days": max(ages) if ages else 0,
            "over_sla_count": len([row for row in rows if row["sla_state"] == "over"]),
        }
