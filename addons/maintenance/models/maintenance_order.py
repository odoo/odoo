from datetime import UTC, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

ORDER_ACTIVITY_TYPE = "maintenance.mail_act_maintenance_order"
OPEN_STATES = ("draft", "confirmed", "in_progress")
CLOSED_STATES = ("done", "cancel")
BOOKING_STATES = ("confirmed", "in_progress")
RESERVATION_FIELDS = frozenset(
    {
        "resource_ids",
        "block_resource",
        "date_scheduled_start",
        "date_scheduled_end",
        "duration",
        "maintenance_type",
        "plan_id",
    }
)


class MaintenanceOrder(models.Model):
    _name = "maintenance.order"
    _inherit = [
        "mixin.mail.thread.cc",
        "mixin.mail.activity",
        "mixin.approval.lifecycle",
        "mixin.resource.scheduling",
    ]
    _description = "Maintenance Order"
    _order = "id desc"
    _check_company_auto = True

    _reservation_sync_manual = True

    _STATE_TRANSITIONS = {
        "draft": {"confirmed", "cancel"},
        "confirmed": {"in_progress", "done", "cancel", "draft"},
        "in_progress": {"done", "cancel"},
        "done": set(),
        "cancel": {"draft"},
    }

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    plan_id = fields.Many2one(
        comodel_name="maintenance.plan",
        index="btree_not_null",
        copy=False,
        ondelete="set null",
        check_company=True,
        tracking=True,
    )
    resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="maintenance_order_resource_rel",
        column1="order_id",
        column2="resource_id",
        string="Maintained Resources",
        domain="[('resource_type', '=', 'material')]",
        check_company=True,
        help="What this order maintains: machines, vehicles, work centres, any material resource. Each is booked, and so is every asset it is part of.",
    )
    asset_ids = fields.Many2many(
        comodel_name="resource.asset",
        string="Assets",
        compute="_compute_asset_ids",
        search="_search_asset_ids",
    )

    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        check_company=True,
        tracking=True,
        help="Supplier performing the maintenance, when it is done outside.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Technician",
        compute="_compute_user_id",
        store=True,
        readonly=False,
        tracking=True,
    )
    maintenance_team_id = fields.Many2one(
        comodel_name="team.team",
        string="Team",
        compute="_compute_maintenance_team_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        domain=[("use_maintenance", "=", True)],
        check_company=True,
    )
    name = fields.Char(
        string="Subjects",
        required=True,
    )
    color = fields.Integer(string="Color Index")
    priority = fields.Selection(
        selection=[("0", "Very Low"), ("1", "Low"), ("2", "Normal"), ("3", "High")]
    )
    description = fields.Html()
    locked = fields.Boolean(tracking=True)
    block_resource = fields.Boolean(
        default=True,
        help="While confirmed or in progress, the scheduled window is unavailable time on every maintained resource, for planning, work orders and every other reader of their calendars.",
    )
    maintenance_type = fields.Selection(
        selection=[("corrective", "Corrective"), ("preventive", "Preventive")],
        default="corrective",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        index=True,
        copy=False,
        readonly=True,
        required=True,
        group_expand=True,
        tracking=True,
    )
    kanban_state = fields.Selection(
        selection=[
            ("normal", "On Track"),
            ("blocked", "Blocked"),
            ("done", "Ready to Continue"),
        ],
        default="normal",
        required=True,
        tracking=True,
    )
    date_confirmed = fields.Datetime(
        string="Confirmation Date",
        compute="_compute_date_confirmed",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="When the order was confirmed, which reliability counts as the failure.",
    )
    date_plan_slot = fields.Datetime(
        string="Plan Slot",
        copy=False,
        readonly=True,
        help="The date of its plan's series this order stands for, however it is rescheduled.",
    )
    date_scheduled_start = fields.Datetime(
        string="Scheduled Start",
        help="Date the maintenance team plans the maintenance. It should not differ much from the Confirmation Date.",
    )
    date_scheduled_end = fields.Datetime(
        string="Scheduled End",
        compute="_compute_date_scheduled_end",
        inverse="_inverse_date_scheduled_end",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Expected completion date and time of the maintenance order.",
    )
    date_done = fields.Date(
        string="Done Date",
        compute="_compute_date_done",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Date the maintenance was finished.",
    )
    duration = fields.Float(
        default=1.0,
        help="Duration in hours.",
    )
    part_ids = fields.One2many(
        comodel_name="resource.asset.part",
        inverse_name="maintenance_order_id",
        string="Parts",
        copy=False,
    )
    part_flagged_count = fields.Integer(
        string="Flagged Parts",
        compute="_compute_part_flagged_count",
    )

    instruction_type = fields.Selection(
        selection=[("pdf", "PDF"), ("google_slide", "Google Slide"), ("text", "Text")],
        string="Instruction",
        default="text",
    )
    instruction_pdf = fields.Binary(string="PDF")
    instruction_google_slide = fields.Char(
        string="Google Slide",
        help="Paste the url of your Google Slide. Make sure the access to the document is public.",
    )
    instruction_text = fields.Html(string="Text")

    @api.constrains("date_scheduled_start", "date_scheduled_end")
    def _check_date_scheduled_end_after_start(self):
        for order in self:
            if (
                order.date_scheduled_start
                and order.date_scheduled_end
                and order.date_scheduled_start > order.date_scheduled_end
            ):
                raise ValidationError(
                    self.env._("End date cannot be earlier than start date.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.filtered("user_id")._add_followers()
        orders.activity_update()
        typed_in = (
            orders.browse()
            if self.ids
            else orders.filtered(lambda order: not order.date_plan_slot)
        )
        typed_in._recreate_reservations()
        (orders - typed_in)._recreate_reservations(refuse_taken_window=False)
        orders.asset_ids._sync_state_from_maintenance()
        return orders

    def write(self, vals):
        if "state" in vals and "kanban_state" not in vals:
            vals = {**vals, "kanban_state": "normal"}
        closing = self.browse()
        if vals.get("state") in CLOSED_STATES:
            closing = self.filtered(lambda order: order.state in OPEN_STATES)
        was_booking = {order.id: order.state in BOOKING_STATES for order in self}
        assets_before = self.asset_ids
        if vals.get("state") == "done":
            for order in self:
                order._get_reservations_ahead().unlink()
        if vals.get("state") == "cancel":
            self.sudo().reservation_ids.unlink()
        res = super().write(vals)
        if "state" in vals:
            self._sync_parts_to_state(vals["state"])
        if not self.env.context.get("skip_maintenance_reservations"):
            if vals.keys() & RESERVATION_FIELDS:
                self._recreate_reservations()
            elif "state" in vals:
                self.filtered(
                    lambda order: (
                        order.state != "done"
                        and (order.state in BOOKING_STATES) != was_booking[order.id]
                    )
                )._recreate_reservations(refuse_taken_window=False)
        if vals.keys() & {"resource_ids", "state"}:
            (self.asset_ids | assets_before)._sync_state_from_maintenance()
        if vals.get("user_id"):
            self._add_followers()
        if closing:
            closing.filtered(lambda order: order.state == "done").activity_feedback(
                [ORDER_ACTIVITY_TYPE]
            )
            # sudo: opening the next occurrence is a consequence of closing this one,
            # not an edit of the plan by whoever closes it.
            for order in closing.filtered("plan_id").sudo():
                order.plan_id._schedule_after(order)
        replace_activity = self._is_new_activity_required(vals)
        if replace_activity:
            self.activity_unlink([ORDER_ACTIVITY_TYPE])
        if replace_activity or vals.keys() & {
            "state",
            "date_scheduled_start",
            "user_id",
        }:
            self.activity_update()
        return res

    def unlink(self):
        plans = self.filtered(lambda order: order.state in OPEN_STATES).plan_id
        assets = self.asset_ids
        res = super().unlink()
        plans.exists().sudo()._create_missing_open_orders()
        assets.exists()._sync_state_from_maintenance()
        return res

    @api.depends("resource_ids")
    def _compute_asset_ids(self):
        assets = self.env["resource.asset"].search(
            [("resource_id", "in", self.resource_ids._origin.ids)]
        )
        for order in self:
            order.asset_ids = assets.filtered(
                lambda asset, resources=order.resource_ids._origin: (
                    asset.resource_id in resources
                )
            )

    @api.depends("part_ids.review_state")
    def _compute_part_flagged_count(self):
        for order in self:
            order.part_flagged_count = len(
                order.part_ids.filtered(lambda part: part.review_state == "flagged")
            )

    @api.depends("state")
    def _compute_date_confirmed(self):
        now = fields.Datetime.now()
        for order in self:
            if order.state == "draft":
                order.date_confirmed = False
            elif order.state != "cancel" and not order.date_confirmed:
                order.date_confirmed = now

    @api.depends("state")
    def _compute_date_done(self):
        today = fields.Date.context_today(self)
        for order in self:
            if order.state != "done":
                order.date_done = False
            elif not order.date_done:
                order.date_done = today

    @api.depends("date_scheduled_start", "duration")
    def _compute_date_scheduled_end(self):
        for order in self:
            order.date_scheduled_end = order.date_scheduled_start and (
                order.date_scheduled_start + timedelta(hours=order.duration or 1)
            )

    @api.depends(
        "company_id",
        "resource_ids.maintenance_team_id",
        "asset_ids.kind_id.maintenance_team_id",
    )
    def _compute_maintenance_team_id(self):
        default_teams = {}
        for order in self:
            team = (
                order.resource_ids.maintenance_team_id.filtered(
                    lambda t, c=order.company_id: not t.company_id or t.company_id == c
                )[:1]
                or order.asset_ids.kind_id.maintenance_team_id[:1]
                or order.maintenance_team_id
            )
            if team.company_id and team.company_id != order.company_id:
                team = team.browse()
            # The company default is the last resort of this precomputed field, not a field
            # default: a field default is filled before the compute, so a create never took the
            # resource's (or an override's) team.
            if not team:
                company = order.company_id
                if company not in default_teams:
                    default_teams[company] = order._get_default_maintenance_team(
                        company
                    )
                team = default_teams[company]
            order.maintenance_team_id = team

    @api.depends(
        "company_id",
        "resource_ids.technician_user_id",
        "asset_ids.kind_id.technician_user_id",
    )
    def _compute_user_id(self):
        for order in self:
            technician = (
                order.resource_ids.technician_user_id[:1]
                or order.asset_ids.kind_id.technician_user_id[:1]
            )
            if technician:
                order.user_id = technician
            if (
                order.user_id
                and order.company_id.id not in order.user_id.company_ids.ids
            ):
                order.user_id = False

    def _inverse_date_scheduled_end(self):
        for order in self:
            if order.date_scheduled_start and order.date_scheduled_end:
                order.duration = (
                    order.date_scheduled_end - order.date_scheduled_start
                ).total_seconds() / 3600

    def _search_asset_ids(self, operator, value):
        if operator not in ("in", "not in", "any", "not any"):
            return NotImplemented
        if operator in ("any", "not any"):
            assets = self.env["resource.asset"].search(value)
        else:
            assets = self.env["resource.asset"].browse(value)
        domain = Domain("resource_ids", "in", assets.resource_id.ids)
        return ~domain if operator.startswith("not") else domain

    def _creation_subtype(self):
        return self.env.ref("maintenance.mt_order_created")

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "state" in init_values:
            return self.env.ref("maintenance.mt_order_state")
        return super()._track_subtype(init_values)

    def action_start(self):
        self.write({"state": "in_progress"})
        return True

    def action_done(self):
        self.write({"state": "done"})
        return True

    def action_view_flagged_parts(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "resource_asset_product.action_resource_asset_part"
        )
        action["domain"] = [("maintenance_order_id", "=", self.id)]
        action["context"] = {"create": False, "search_default_flagged": 1}
        return action

    def _sync_parts_to_state(self, state):
        parts = self.part_ids
        _debug.lifecycle(
            "order_parts_follow_state", orders=self, state=state, parts=parts
        )
        if state == "done":
            planned = parts.filtered(lambda part: part.state == "draft")
            for order in self:
                order._prepare_parts_for_installation(
                    planned.filtered(
                        lambda part, o=order: part.maintenance_order_id == o
                    )
                )
            planned._action_install()
            planned._flag_not_returned()
        elif state == "cancel":
            parts.filtered(lambda part: part.state == "draft").action_cancel()
        elif state == "draft":
            parts.filtered(lambda part: part.state == "cancelled").action_draft()

    def _prepare_parts_for_installation(self, parts):
        self.check_singleton()
        _debug.logic(
            "order_parts_installer",
            order=self,
            parts=parts,
            vendor=self.vendor_id,
            technician=self.user_id,
        )
        if self.vendor_id:
            parts.filtered(lambda part: not part.vendor_id).vendor_id = self.vendor_id
        elif self.user_id:
            parts.filtered(
                lambda part: not part.vendor_id and not part.user_id
            ).user_id = self.user_id
        parts.filtered(lambda part: part.source == "manual").source = "maintenance"

    def _prepare_confirmation_values(self):
        return {"state": "confirmed"}

    def _get_domain_approval_category(self):
        self.check_singleton()
        return [
            ("active", "=", True),
            ("approval_type", "=", f"maintenance_{self.maintenance_type}"),
            ("target_model", "=", False),
        ]

    def _get_fields_approval_protected(self):
        return ["resource_ids", "maintenance_type"]

    @api.model
    def _get_domain_open(self):
        return [("state", "in", OPEN_STATES)]

    @api.model
    def _get_default_maintenance_team(self, company):
        return (
            self.env["team.team"]
            .with_company(company)
            .search(
                [
                    ("use_maintenance", "=", True),
                    ("company_id", "in", [company.id, False]),
                ],
                order="company_id NULLS LAST, id",
                limit=1,
            )
        )

    def get_plan_occurrences(self, start, stop):
        start, stop = (
            fields.Datetime.to_datetime(start),
            fields.Datetime.to_datetime(stop),
        )
        occurrences = {}
        for plan in self.plan_id.sudo().filtered("active"):
            latest = plan._get_open_orders()[-1:]
            base = plan._get_projection_base()
            if latest.id not in self.ids or not base:
                continue
            occurrences[latest.id] = [
                fields.Datetime.to_string(occurrence)
                for occurrence in plan._get_occurrences_after(base, stop=stop)
                if occurrence >= start
            ]
        return occurrences

    def _get_activity_note(self):
        self.check_singleton()
        if self.asset_ids:
            return _(
                "Order planned for %s",
                ", ".join(asset._get_html_link() for asset in self.asset_ids),
            )
        return False

    def _get_fields_reservation_date(self):
        return ("date_scheduled_start", "date_scheduled_end")

    def _get_booked_resources(self):
        self.check_singleton()
        resources = self.resource_ids
        assets = self.asset_ids.parent_id
        while assets:
            resources |= assets.resource_id
            assets = assets.parent_id
        return resources

    def _get_reservations_ahead(self):
        self.check_singleton()
        reservations = self.sudo().with_context(active_test=False).reservation_ids
        if not reservations:
            return reservations
        first = min(reservations.mapped("date_start"))
        return reservations.filtered(lambda r: r.date_start != first)

    def _get_occurrences_to_book(self):
        self.check_singleton()
        dates = [self.date_scheduled_start]
        plan = self.plan_id
        if (
            plan.active
            and plan.repeat_anchor == "fixed"
            and plan.book_ahead_count > 0
            and self.maintenance_type == "preventive"
        ):
            dates += plan._get_occurrences_after(
                max(
                    self.date_plan_slot or self.date_scheduled_start,
                    self.date_scheduled_start,
                ),
                limit=plan.book_ahead_count,
            )
        return dates

    def _recreate_reservations(self, refuse_taken_window=True):
        self.sudo().reservation_ids.unlink()
        Reservation = self.env["resource.reservation"].sudo()
        for order in self:
            resources = order._get_booked_resources()
            if (
                not resources
                or not order.block_resource
                or not order.date_scheduled_start
                or order.state not in BOOKING_STATES
            ):
                continue
            desired = order.date_scheduled_start
            hours = order.duration or 1
            if refuse_taken_window:
                start, _end = resources._find_free_window(desired, hours)
                if start != desired:
                    raise UserError(
                        self.env._(
                            "%(resources)s already booked at that time: choose another window for %(order)s.",
                            resources=", ".join(resources.mapped("name")),
                            order=order.display_name,
                        )
                    )
            first = None
            missing = False
            for occurrence in order._get_occurrences_to_book():
                start, end = resources._find_free_window(occurrence, hours)
                if not start:
                    missing = True
                    break
                Reservation.create(
                    [
                        {
                            "name": order.display_name,
                            "res_model": order._name,
                            "res_id": order.id,
                            "resource_id": resource.id,
                            "date_start": start,
                            "date_end": end,
                            "allocated_percentage": 100.0,
                            "enforcement_mode": "hard",
                        }
                        for resource in resources
                    ]
                )
                first = first or (start, end)
            order.invalidate_recordset(["reservation_ids", "schedule_overlap_count"])
            if first and first[0] != desired:
                order.with_context(skip_maintenance_reservations=True).write(
                    {"date_scheduled_start": first[0], "date_scheduled_end": first[1]}
                )
            if missing or (first and first[0] != desired):
                order._warn_rescheduled(desired, first, missing)

    def _warn_rescheduled(self, desired, first, missing):
        self.check_singleton()
        if missing:
            note = self.env._("No free window within 700 days after the planned start.")
        else:
            tz = timezone(self.env.user.tz or "UTC")
            note = self.env._(
                "The schedule moved from %(desired)s to %(effective)s, past what already booked its resources.",
                desired=desired.replace(tzinfo=UTC).astimezone(tz),
                effective=first[0].replace(tzinfo=UTC).astimezone(tz),
            )
        self.activity_schedule(
            "mail.mail_activity_data_warning", note=note, user_id=self.env.uid
        )

    def activity_update(self):
        """Update maintenance activities based on current record set state.
        It reschedule, unlink or create maintenance order activities."""
        planned = self.filtered(
            lambda order: order.date_scheduled_start and order.state in OPEN_STATES
        )
        (self - planned).activity_unlink([ORDER_ACTIVITY_TYPE])
        Activity = self.env["mail.activity"]
        for order in planned:
            assignee = order.user_id or order.create_uid or self.env.user
            deadline = Activity._today_in_tz(
                assignee.sudo().tz, order.date_scheduled_start.replace(tzinfo=UTC)
            )
            if not order.activity_reschedule(
                [ORDER_ACTIVITY_TYPE],
                date_deadline=deadline,
                new_user_id=assignee.id,
            ):
                order.activity_schedule(
                    ORDER_ACTIVITY_TYPE,
                    deadline,
                    note=order._get_activity_note(),
                    user_id=assignee.id,
                )

    def _add_followers(self):
        for order in self:
            order.message_subscribe(partner_ids=order.user_id.partner_id.ids)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = dict(custom_values or {})
        team = self.env["team.team"].browse(values.get("maintenance_team_id") or ())
        if team.company_id and "company_id" not in values:
            values["company_id"] = team.company_id.id
        return super().message_new(msg_dict, custom_values=values)

    def _is_new_activity_required(self, vals):
        return vals.get("resource_ids")
