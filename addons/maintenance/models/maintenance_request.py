from datetime import UTC, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

REQUEST_ACTIVITY_TYPE = "maintenance.mail_act_maintenance_request"


class MaintenanceRequest(models.Model):
    _name = "maintenance.request"
    _inherit = ["mixin.mail.thread.cc", "mixin.mail.activity"]
    _description = "Maintenance Request"
    _order = "id desc"
    _check_company_auto = True

    def _default_stage_id(self):
        return self.env["maintenance.stage"].search([], limit=1)

    def _creation_subtype(self):
        return self.env.ref("maintenance.mt_req_created")

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "stage_id" in init_values:
            return self.env.ref("maintenance.mt_req_status")
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
    request_date = fields.Date(
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
    stage_id = fields.Many2one(
        comodel_name="maintenance.stage",
        default=_default_stage_id,
        copy=False,
        group_expand="_read_group_stage_ids",
        ondelete="restrict",
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
            ("normal", "In Progress"),
            ("blocked", "Blocked"),
            ("done", "Ready for next stage"),
        ],
        default="normal",
        required=True,
        tracking=True,
    )
    archive = fields.Boolean(
        default=False,
        help="Set archive to true to hide the maintenance request without deleting it.",
    )
    maintenance_type = fields.Selection(
        selection=[("corrective", "Corrective"), ("preventive", "Preventive")],
        default="corrective",
    )
    schedule_date = fields.Datetime(
        string="Scheduled Date",
        help="Date the maintenance team plans the maintenance.  It should not differ much from the Request Date. ",
    )
    schedule_end = fields.Datetime(
        string="Scheduled End",
        compute="_compute_schedule_end",
        inverse="_inverse_schedule_end",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="Expected completion date and time of the maintenance request.",
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
    done = fields.Boolean(related="stage_id.done")
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
        ondelete="set null",
        check_company=True,
        tracking=True,
    )

    def archive_equipment_request(self):
        self.write({"archive": True})

    def reset_equipment_request(self):
        """Reinsert the maintenance request into the maintenance pipe in the first stage"""
        self.write({"archive": False, "stage_id": self._default_stage_id().id})

    @api.model
    def _get_domain_open(self):
        return [("stage_id.done", "=", False), ("archive", "=", False)]

    @api.constrains("schedule_date", "schedule_end")
    def _check_schedule_end_after_start(self):
        for request in self:
            if (
                request.schedule_date
                and request.schedule_end
                and request.schedule_date > request.schedule_end
            ):
                raise ValidationError(
                    self.env._("End date cannot be earlier than start date.")
                )

    @api.depends("stage_id")
    def _compute_close_date(self):
        today = fields.Date.context_today(self)
        for request in self:
            if not request.stage_id.done:
                request.close_date = False
            elif not request.close_date:
                request.close_date = today

    @api.depends("schedule_date", "duration")
    def _compute_schedule_end(self):
        for request in self:
            request.schedule_end = request.schedule_date and (
                request.schedule_date + timedelta(hours=request.duration or 1)
            )

    def _inverse_schedule_end(self):
        for request in self:
            if request.schedule_date and request.schedule_end:
                request.duration = (
                    request.schedule_end - request.schedule_date
                ).total_seconds() / 3600

    @api.depends("company_id", "equipment_id")
    def _compute_maintenance_team_id(self):
        default_teams = {}
        for request in self:
            team = (
                request.equipment_id.maintenance_team_id or request.maintenance_team_id
            )
            if team.company_id and team.company_id != request.company_id:
                team = team.browse()
            # The company default is the last resort of this precomputed field, not a field
            # default: a field default is filled before the compute, so a create never took the
            # equipment's (or an override's) team.
            if not team:
                company = request.company_id
                if company not in default_teams:
                    default_teams[company] = request._get_default_maintenance_team(
                        company
                    )
                team = default_teams[company]
            request.maintenance_team_id = team

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
        for request in self:
            if request.equipment_id:
                request.user_id = (
                    request.equipment_id.technician_user_id
                    or request.equipment_id.category_id.technician_user_id
                )
            if (
                request.user_id
                and request.company_id.id not in request.user_id.company_ids.ids
            ):
                request.user_id = False

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        requests.filtered(
            lambda request: request.owner_user_id or request.user_id
        )._add_followers()
        requests.activity_update()
        return requests

    def write(self, vals):
        if "stage_id" in vals and "kanban_state" not in vals:
            vals = {**vals, "kanban_state": "normal"}
        closing = self.browse()
        if (
            "stage_id" in vals
            and self.env["maintenance.stage"].browse(vals["stage_id"]).done
        ):
            closing = self.filtered(lambda request: not request.stage_id.done)
        if vals.get("archive"):
            closing |= self.filtered(
                lambda request: not request.archive and not request.stage_id.done
            )
        res = super().write(vals)
        if vals.get("owner_user_id") or vals.get("user_id"):
            self._add_followers()
        if closing:
            closing.filtered("stage_id.done").activity_feedback([REQUEST_ACTIVITY_TYPE])
            for request in closing.filtered("plan_id"):
                request.plan_id._schedule_after(request)
        replace_activity = self._is_new_activity_required(vals)
        if replace_activity:
            self.activity_unlink([REQUEST_ACTIVITY_TYPE])
        if replace_activity or vals.keys() & {
            "stage_id",
            "archive",
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
        return {
            request.id: [
                fields.Datetime.to_string(occurrence)
                for occurrence in request.plan_id._get_occurrences_after(
                    request.schedule_date, stop=stop
                )
                if occurrence >= start
            ]
            for request in self.filtered(
                lambda request: (
                    request.plan_id.active
                    and request.schedule_date
                    and not request.stage_id.done
                    and not request.archive
                )
            )
        }

    def _is_new_activity_required(self, vals):
        return vals.get("equipment_id")

    def _get_activity_note(self):
        self.check_singleton()
        if self.equipment_id:
            return _("Request planned for %s", self.equipment_id._get_html_link())
        return False

    def activity_update(self):
        """Update maintenance activities based on current record set state.
        It reschedule, unlink or create maintenance request activities."""
        planned = self.filtered(
            lambda request: (
                request.schedule_date
                and not request.archive
                and not request.stage_id.done
            )
        )
        (self - planned).activity_unlink([REQUEST_ACTIVITY_TYPE])
        Activity = self.env["mail.activity"]
        for request in planned:
            assignee = request.user_id or request.owner_user_id or self.env.user
            deadline = Activity._today_in_tz(
                assignee.sudo().tz, request.schedule_date.replace(tzinfo=UTC)
            )
            if not request.activity_reschedule(
                [REQUEST_ACTIVITY_TYPE],
                date_deadline=deadline,
                new_user_id=assignee.id,
            ):
                request.activity_schedule(
                    REQUEST_ACTIVITY_TYPE,
                    deadline,
                    note=request._get_activity_note(),
                    user_id=assignee.id,
                )

    def _add_followers(self):
        for request in self:
            partner_ids = (
                request.owner_user_id.partner_id + request.user_id.partner_id
            ).ids
            request.message_subscribe(partner_ids=partner_ids)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = dict(custom_values or {})
        team = self.env["team.team"].browse(values.get("maintenance_team_id") or ())
        if team.company_id and "company_id" not in values:
            values["company_id"] = team.company_id.id
        return super().message_new(msg_dict, custom_values=values)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Read group customization in order to display all the stages in the
        kanban view, even if they are empty
        """
        stage_ids = stages.sudo()._search([], order=stages._order)
        return stages.browse(stage_ids)
