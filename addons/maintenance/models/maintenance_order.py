from datetime import UTC, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

ORDER_ACTIVITY_TYPE = "maintenance.mail_act_maintenance_order"
OPEN_STATES = ("draft", "confirmed", "in_progress")
CLOSED_STATES = ("done", "cancel")
BOOKING_STATES = ("confirmed", "in_progress")


class MaintenanceOrder(models.Model):
    _name = "maintenance.order"
    _inherit = [
        "mixin.mail.thread.cc",
        "mixin.mail.activity",
        "mixin.approval.lifecycle",
    ]
    _description = "Maintenance Order"
    _order = "id desc"
    _check_company_auto = True

    _STATE_TRANSITIONS = {
        "draft": {"confirmed", "cancel"},
        "confirmed": {"in_progress", "done", "cancel", "draft"},
        "in_progress": {"done", "cancel"},
        "done": set(),
        "cancel": {"draft"},
    }

    def _creation_subtype(self):
        return self.env.ref("maintenance.mt_order_created")

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "state" in init_values:
            return self.env.ref("maintenance.mt_order_state")
        return super()._track_subtype(init_values)

    name = fields.Char(
        string="Subjects",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    description = fields.Html()
    date_order = fields.Date(
        default=fields.Date.context_today,
        tracking=True,
        help="Date requested for the maintenance to happen",
    )
    owner_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Created by User",
        default=lambda s: s.env.uid,
    )
    category_id = fields.Many2one(
        comodel_name="maintenance.equipment.category",
        related="equipment_id.category_id",
        string="Category",
        store=True,
        index="btree_not_null",
        readonly=True,
    )
    equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        index=True,
        ondelete="restrict",
        check_company=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Technician",
        compute="_compute_user_id",
        store=True,
        readonly=False,
        tracking=True,
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
    priority = fields.Selection(
        selection=[("0", "Very Low"), ("1", "Low"), ("2", "Normal"), ("3", "High")]
    )
    color = fields.Integer(string="Color Index")
    close_date = fields.Date(
        compute="_compute_close_date",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Date the maintenance was finished.",
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
    maintenance_type = fields.Selection(
        selection=[("corrective", "Corrective"), ("preventive", "Preventive")],
        default="corrective",
    )
    schedule_date = fields.Datetime(
        string="Scheduled Date",
        help="Date the maintenance team plans the maintenance.  It should not differ much from the Order Date. ",
    )
    schedule_end = fields.Datetime(
        string="Scheduled End",
        compute="_compute_schedule_end",
        inverse="_inverse_schedule_end",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Expected completion date and time of the maintenance order.",
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
    duration = fields.Float(
        default=1.0,
        help="Duration in hours.",
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
    plan_id = fields.Many2one(
        comodel_name="maintenance.plan",
        index="btree_not_null",
        copy=False,
        ondelete="set null",
        check_company=True,
        tracking=True,
    )
    date_occurrence = fields.Datetime(
        string="Planned Occurrence",
        copy=False,
        readonly=True,
        help="The date of its plan's series this order stands for, however it is rescheduled.",
    )

    def _prepare_confirmation_values(self):
        return {"state": "confirmed"}

    def action_start(self):
        self.write({"state": "in_progress"})
        return True

    def action_done(self):
        self.write({"state": "done"})
        return True

    def _get_domain_approval_category(self):
        self.check_singleton()
        return [
            ("active", "=", True),
            ("approval_type", "=", f"maintenance_{self.maintenance_type}"),
            ("target_model", "=", False),
        ]

    def _get_fields_approval_protected(self):
        return ["equipment_id", "maintenance_type"]

    @api.model
    def _get_domain_open(self):
        return [("state", "in", OPEN_STATES)]

    @api.constrains("schedule_date", "schedule_end")
    def _check_schedule_end_after_start(self):
        for order in self:
            if (
                order.schedule_date
                and order.schedule_end
                and order.schedule_date > order.schedule_end
            ):
                raise ValidationError(
                    self.env._("End date cannot be earlier than start date.")
                )

    @api.depends("state")
    def _compute_close_date(self):
        today = fields.Date.context_today(self)
        for order in self:
            if order.state != "done":
                order.close_date = False
            elif not order.close_date:
                order.close_date = today

    @api.depends("schedule_date", "duration")
    def _compute_schedule_end(self):
        for order in self:
            order.schedule_end = order.schedule_date and (
                order.schedule_date + timedelta(hours=order.duration or 1)
            )

    def _inverse_schedule_end(self):
        for order in self:
            if order.schedule_date and order.schedule_end:
                order.duration = (
                    order.schedule_end - order.schedule_date
                ).total_seconds() / 3600

    @api.depends("company_id", "equipment_id")
    def _compute_maintenance_team_id(self):
        default_teams = {}
        for order in self:
            team = order.equipment_id.maintenance_team_id or order.maintenance_team_id
            if team.company_id and team.company_id != order.company_id:
                team = team.browse()
            # The company default is the last resort of this precomputed field, not a field
            # default: a field default is filled before the compute, so a create never took the
            # equipment's (or an override's) team.
            if not team:
                company = order.company_id
                if company not in default_teams:
                    default_teams[company] = order._get_default_maintenance_team(
                        company
                    )
                team = default_teams[company]
            order.maintenance_team_id = team

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

    @api.depends("company_id", "equipment_id")
    def _compute_user_id(self):
        for order in self:
            if order.equipment_id:
                order.user_id = (
                    order.equipment_id.technician_user_id
                    or order.equipment_id.category_id.technician_user_id
                )
            if (
                order.user_id
                and order.company_id.id not in order.user_id.company_ids.ids
            ):
                order.user_id = False

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.filtered(
            lambda order: order.owner_user_id or order.user_id
        )._add_followers()
        orders.activity_update()
        return orders

    def write(self, vals):
        if "state" in vals and "kanban_state" not in vals:
            vals = {**vals, "kanban_state": "normal"}
        closing = self.browse()
        if vals.get("state") in CLOSED_STATES:
            closing = self.filtered(lambda order: order.state in OPEN_STATES)
        res = super().write(vals)
        if vals.get("owner_user_id") or vals.get("user_id"):
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
            "schedule_date",
            "user_id",
            "owner_user_id",
        }:
            self.activity_update()
        return res

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

    def unlink(self):
        plans = self.filtered(lambda order: order.state in OPEN_STATES).plan_id
        res = super().unlink()
        plans.exists().sudo()._ensure_open_order()
        return res

    def _is_new_activity_required(self, vals):
        return vals.get("equipment_id")

    def _get_activity_note(self):
        self.check_singleton()
        if self.equipment_id:
            return _("Order planned for %s", self.equipment_id._get_html_link())
        return False

    def activity_update(self):
        """Update maintenance activities based on current record set state.
        It reschedule, unlink or create maintenance order activities."""
        planned = self.filtered(
            lambda order: order.schedule_date and order.state in OPEN_STATES
        )
        (self - planned).activity_unlink([ORDER_ACTIVITY_TYPE])
        Activity = self.env["mail.activity"]
        for order in planned:
            assignee = order.user_id or order.owner_user_id or self.env.user
            deadline = Activity._today_in_tz(
                assignee.sudo().tz, order.schedule_date.replace(tzinfo=UTC)
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
            partner_ids = (
                order.owner_user_id.partner_id + order.user_id.partner_id
            ).ids
            order.message_subscribe(partner_ids=partner_ids)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = dict(custom_values or {})
        team = self.env["team.team"].browse(values.get("maintenance_team_id") or ())
        if team.company_id and "company_id" not in values:
            values["company_id"] = team.company_id.id
        return super().message_new(msg_dict, custom_values=values)
