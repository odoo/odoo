from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

from .utils import CUSTODY_SYNC, EXCLUSIVE_CUSTODY_ROLES


class ResourceAssignment(models.Model):
    _name = "resource.assignment"
    _description = "Resource Assignment"
    _inherit = ["mixin.resource.scheduling"]
    _order = "date_start desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    active = fields.Boolean(default=True)
    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        index=True,
        required=True,
        ondelete="restrict",
        check_company=True,
        help="What is held: a vehicle, a machine, a room, a device.",
    )
    assignee_id = fields.Many2one(
        comodel_name="resource.resource",
        index=True,
        domain="[('resource_type', '=', 'user')]",
        ondelete="restrict",
        check_company=True,
        help="Who holds it.",
    )
    assignee_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Holder",
        compute="_compute_assignee_partner_id",
        store=True,
        readonly=False,
        domain="[('is_company', '=', False)]",
        help="The person who holds it. Anyone can: picking a person gives them a human resource in the company of what they hold.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="resource_id.company_id",
    )
    custody_role = fields.Selection(
        selection=[
            ("custodian", "Custodian"),
            ("operator", "Operator"),
            ("manager", "Manager"),
            ("technician", "Technician"),
        ],
        default="custodian",
        required=True,
    )
    date_start = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        required=True,
    )
    date_end = fields.Datetime(index=True)
    state = fields.Selection(
        selection=[("planned", "Planned"), ("active", "Active"), ("ended", "Ended")],
        compute="_compute_state",
        search="_search_state",
    )
    note = fields.Text()

    _resource_period_idx = models.Index("(resource_id, date_start, date_end)")
    _check_dates = models.Constraint(
        "CHECK(date_end IS NULL OR date_end >= date_start)",
        "An assignment cannot end before it starts.",
    )

    @api.constrains("resource_id", "assignee_id")
    def _check_parties(self):
        for record in self:
            if not record._has_holder():
                raise ValidationError(
                    self.env._(
                        "%(resource)s is assigned to nobody: name who holds it.",
                        resource=record.resource_id.name,
                    )
                )
            if not record.assignee_id:
                continue
            if record.resource_id == record.assignee_id:
                raise ValidationError(
                    self.env._("A resource cannot be assigned to itself.")
                )
            if record.assignee_id.resource_type != "user":
                raise ValidationError(
                    self.env._(
                        "%(name)s is not a human resource and cannot hold an assignment.",
                        name=record.assignee_id.name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        self._update_assignee_vals(vals_list)
        assignments = super().create(vals_list)
        if not self.env.context.get(CUSTODY_SYNC):
            assignments._supersede_rivals()
        return assignments

    def write(self, vals):
        if "assignee_partner_id" not in vals:
            return super().write(vals)
        vals = dict(vals)
        party = self.env["res.partner"].browse(vals.pop("assignee_partner_id"))
        if not party:
            return super().write({**vals, "assignee_id": False})
        resource = self.env["resource.resource"].browse(vals.get("resource_id"))
        by_company = self.grouped(
            lambda record: (resource or record.resource_id).company_id
        )
        for company, records in by_company.items():
            holder = party.sudo()._get_or_create_resources(company)
            super(ResourceAssignment, records).write({**vals, "assignee_id": holder.id})
        return True

    @api.depends("assignee_id.partner_id")
    def _compute_assignee_partner_id(self):
        for record in self:
            record.assignee_partner_id = record.assignee_id.partner_id

    @api.depends("resource_id.name", "assignee_id.name", "custody_role")
    @api.depends_context("lang")
    def _compute_name(self):
        roles = dict(self._fields["custody_role"]._description_selection(self.env))
        for record in self:
            record.name = self.env._(
                "%(assignee)s, %(role)s of %(resource)s",
                assignee=record._get_holder_name() or "?",
                role=roles.get(record.custody_role, record.custody_role),
                resource=record.resource_id.name or "?",
            )

    @api.depends("date_start", "date_end", "active")
    def _compute_state(self):
        now = fields.Datetime.now()
        for record in self:
            if record.date_start and record.date_start > now:
                record.state = "planned"
            elif record.date_end and record.date_end <= now:
                record.state = "ended"
            else:
                record.state = "active"

    def _end(self, at=None):
        at = at or fields.Datetime.now()
        started = self.filtered(lambda a: a.date_start <= at)
        started.write({"date_end": at})
        for planned in self - started:
            planned.date_end = planned.date_start

    @api.model
    def _get_exclusive_custody_roles(self) -> tuple[str, ...]:
        return EXCLUSIVE_CUSTODY_ROLES

    @api.model
    def _get_custody_domain(self, at=None, when="live"):
        at = at or fields.Datetime.now()
        not_ended = Domain("date_end", "=", False) | Domain("date_end", ">", at)
        if when == "live":
            return Domain("date_start", "<=", at) & not_ended
        if when == "planned":
            return Domain("date_start", ">", at) & Domain("date_end", "=", False)
        if when == "open":
            return not_ended
        raise ValueError(when)

    def _get_first_by_resource(self, reverse=True):
        first = {}
        for assignment in self.sorted("date_start", reverse=reverse):
            first.setdefault(assignment.resource_id.id, assignment)
        return first

    def _get_holder_name(self):
        self.check_singleton()
        return self.assignee_id.name

    def _get_fields_reservation_date(self):
        return ("date_start", "date_end")

    def _get_fields_sync_trigger(self):
        return super()._get_fields_sync_trigger() | {"resource_id", "name"}

    @api.model
    def _get_holder(self, resource, custody_role=None, at=None):
        at = at or fields.Datetime.now()
        domain = (
            Domain("resource_id", "=", resource.id)
            & Domain("date_start", "<=", at)
            & (Domain("date_end", "=", False) | Domain("date_end", ">", at))
        )
        if custody_role:
            domain &= Domain("custody_role", "=", custody_role)
        return self.search(domain, order="date_start desc", limit=1).assignee_id

    @api.model
    def _search_custody(
        self, resources, roles=None, at=None, when="live", archived=False
    ):
        if not resources:
            return self.browse()
        domain = Domain("resource_id", "in", resources.ids) & self._get_custody_domain(
            at, when
        )
        if roles:
            domain &= Domain("custody_role", "in", list(roles))
        assignments = self.sudo()
        if archived:
            assignments = assignments.with_context(active_test=False)
        return assignments.search(domain)

    def _prepare_reservation_vals_list(self):
        self.check_singleton()
        if not self.date_start or not self.date_end or not self.resource_id:
            return []
        return [
            {
                "name": self.name,
                "date_start": self.date_start,
                "date_end": self.date_end,
                "resource_id": self.resource_id.id,
                "allocated_percentage": 100.0 / (self.resource_id.capacity or 1),
                "enforcement_mode": "soft",
            }
        ]

    def _supersede_rivals(self, at=None):
        at = at or fields.Datetime.now()
        exclusive = self._get_exclusive_custody_roles()
        started = self.filtered(
            lambda assignment: (
                assignment.custody_role in exclusive
                and assignment.date_start <= at
                and (not assignment.date_end or assignment.date_end > at)
            )
        )
        if not started:
            return
        keys = {(a.resource_id.id, a.custody_role) for a in started}
        rivals = (
            self._search_custody(started.resource_id, roles=exclusive, at=at) - self
        ).filtered(lambda rival: (rival.resource_id.id, rival.custody_role) in keys)
        rivals._end(at)

    def _search_state(self, operator, value):
        if operator not in ("=", "!=", "in", "not in"):
            return NotImplemented
        values = {value} if isinstance(value, str) else set(value or ())
        now = fields.Datetime.now()
        by_state = {
            "planned": Domain("date_start", ">", now),
            "ended": Domain("date_end", "!=", False) & Domain("date_end", "<=", now),
        }
        by_state["active"] = ~(by_state["planned"] | by_state["ended"])
        domain = (
            Domain.OR(by_state[v] for v in values if v in by_state)
            if values
            else Domain.FALSE
        )
        if operator in ("!=", "not in"):
            domain = ~domain
        return domain

    def _update_assignee_vals(self, vals_list):
        default_resource_id = self.env.context.get("default_resource_id")
        pending = defaultdict(list)
        for vals in vals_list:
            party_id = vals.pop("assignee_partner_id", None)
            if not party_id or vals.get("assignee_id"):
                continue
            resource = self.env["resource.resource"].browse(
                vals.get("resource_id") or default_resource_id
            )
            pending[resource.company_id].append((vals, party_id))
        for company, entries in pending.items():
            parties = self.env["res.partner"].browse(
                [party_id for _vals, party_id in entries]
            )
            holders = parties.sudo()._get_or_create_resources(company)
            for (vals, _party_id), holder in zip(entries, holders, strict=True):
                vals["assignee_id"] = holder.id

    def _has_holder(self):
        self.check_singleton()
        return bool(self.assignee_id)
