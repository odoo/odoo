from collections import defaultdict
from datetime import UTC

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

REQUEST_ACTIVITY_TYPE = "maintenance.mail_act_maintenance_request"


class MaintenanceStage(models.Model):
    """Model for case stages. This models the main stages of a Maintenance Request management flow."""

    _name = "maintenance.stage"
    _description = "Maintenance Stage"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=20)
    fold = fields.Boolean(string="Folded in Maintenance Pipe")
    done = fields.Boolean(string="Request Done")


class MaintenanceEquipmentCategory(models.Model):
    _name = "maintenance.equipment.category"
    _description = "Maintenance Equipment Category"

    name = fields.Char(
        string="Category Name",
        translate=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    technician_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.uid,
    )
    color = fields.Integer(string="Color Index")
    note = fields.Html(
        string="Comments",
        translate=True,
    )
    equipment_ids = fields.One2many(
        comodel_name="maintenance.equipment",
        inverse_name="category_id",
        copy=False,
    )
    equipment_count = fields.Integer(compute="_compute_equipment_count")
    maintenance_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="category_id",
        copy=False,
    )
    maintenance_count = fields.Integer(compute="_compute_maintenance_counts")
    maintenance_open_count = fields.Integer(
        string="Current Maintenance",
        compute="_compute_maintenance_counts",
    )
    fold = fields.Boolean(
        string="Folded in Maintenance Pipe",
        compute="_compute_fold",
        store=True,
    )
    equipment_properties_definition = fields.PropertiesDefinition(
        string="Equipment Properties"
    )

    @api.depends("equipment_ids.active")
    def _compute_fold(self):
        for category in self:
            category.fold = not category.equipment_ids

    def _compute_equipment_count(self):
        equipment_data = self.env["maintenance.equipment"]._read_group(
            [("category_id", "in", self.ids)], ["category_id"], ["__count"]
        )
        mapped_data = {category.id: count for category, count in equipment_data}
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)

    def _compute_maintenance_counts(self):
        Request = self.env["maintenance.request"]
        domain = [("category_id", "in", self.ids)]
        total = dict(Request._read_group(domain, ["category_id"], ["__count"]))
        open_ = dict(
            Request._read_group(
                domain + Request._get_domain_open(), ["category_id"], ["__count"]
            )
        )
        for category in self:
            category.maintenance_count = total.get(category, 0)
            category.maintenance_open_count = open_.get(category, 0)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_maintenance_requests(self):
        if any(
            category.with_context(active_test=False).equipment_ids
            or category.maintenance_ids
            for category in self
        ):
            raise UserError(
                _(
                    "You can’t delete an equipment category if some equipment or maintenance requests are linked to it."
                )
            )


class MaintenanceEquipment(models.Model):
    _name = "maintenance.equipment"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.maintenance"]
    _description = "Maintenance Equipment"
    _check_company_auto = True

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "owner_user_id" in init_values and self.owner_user_id:
            return self.env.ref("maintenance.mt_mat_assign")
        return super()._track_subtype(init_values)

    @api.depends("serial_no")
    def _compute_display_name(self):
        for record in self:
            if record.serial_no:
                record.display_name = (record.name or "") + "/" + record.serial_no
            else:
                record.display_name = record.name

    name = fields.Char(
        string="Equipment Name",
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    owner_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        index="btree_not_null",
        tracking=True,
    )
    category_id = fields.Many2one(
        comodel_name="maintenance.equipment.category",
        string="Equipment Category",
        index="btree_not_null",
        group_expand="_read_group_category_ids",
        tracking=True,
    )
    technician_user_id = fields.Many2one(
        compute="_compute_technician_user_id",
        precompute=True,
        store=True,
        readonly=False,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        check_company=True,
    )
    partner_ref = fields.Char(string="Vendor Reference")
    model = fields.Char()
    serial_no = fields.Char(
        string="Serial Number",
        copy=False,
    )
    assign_date = fields.Date(
        string="Assigned Date",
        tracking=True,
    )
    cost = fields.Float()
    note = fields.Html()
    warranty_date = fields.Date(string="Warranty Expiration Date")
    color = fields.Integer(string="Color Index")
    scrap_date = fields.Date()
    maintenance_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="equipment_id",
    )
    equipment_properties = fields.Properties(
        definition="category_id.equipment_properties_definition",
        string="Properties",
        copy=True,
    )

    _serial_no = models.Constraint(
        "unique(serial_no)",
        "Another asset already exists with this serial number!",
    )

    @api.depends("category_id")
    def _compute_technician_user_id(self):
        for equipment in self:
            equipment.technician_user_id = (
                equipment.category_id.technician_user_id or equipment.technician_user_id
            )

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        for equipment in equipments:
            if equipment.owner_user_id:
                equipment.message_subscribe(
                    partner_ids=[equipment.owner_user_id.partner_id.id]
                )
        return equipments

    def write(self, vals):
        if vals.get("owner_user_id"):
            self.message_subscribe(
                partner_ids=self.env["res.users"]
                .browse(vals["owner_user_id"])
                .partner_id.ids
            )
        return super().write(vals)

    @api.model
    def _read_group_category_ids(self, categories, domain):
        """Read group customization in order to display all the categories in
        the kanban view, even if they are empty.
        """
        # bypass ir.model.access checks, but search with ir.rules
        search_domain = self.env["ir.rule"]._get_domain_accessible_records(
            categories._name
        )
        category_ids = categories.sudo()._search(search_domain, order=categories._order)
        return categories.browse(category_ids)


class MaintenanceRequest(models.Model):
    _name = "maintenance.request"
    _inherit = ["mixin.mail.thread.cc", "mixin.mail.activity", "mixin.recurrence.rule"]
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
        store=True,
        readonly=False,
        help="Expected completion date and time of the maintenance request.",
    )
    maintenance_team_id = fields.Many2one(
        comodel_name="maintenance.team",
        string="Team",
        compute="_compute_maintenance_team_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        check_company=True,
    )
    duration = fields.Float(
        compute="_compute_duration",
        store=True,
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
    recurring_maintenance = fields.Boolean(
        string="Recurrent",
        compute="_compute_recurring_maintenance",
        store=True,
        readonly=False,
    )
    repeat_until = fields.Date(string="End Date")

    def archive_equipment_request(self):
        self.write({"archive": True, "recurring_maintenance": False})

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

    @api.constrains("recurring_maintenance", "repeat_type", "repeat_until")
    def _check_until_recurrence_has_end_date(self):
        if self.filtered(
            lambda request: (
                request.recurring_maintenance
                and request.repeat_type == "until"
                and not request.repeat_until
            )
        ):
            raise ValidationError(
                self.env._("A recurrence repeated until a date needs its end date.")
            )

    @api.depends("stage_id")
    def _compute_close_date(self):
        today = fields.Date.context_today(self)
        for request in self:
            if not request.stage_id.done:
                request.close_date = False
            elif not request.close_date:
                request.close_date = today

    @api.depends("schedule_date")
    def _compute_schedule_end(self):
        for request in self:
            request.schedule_end = (
                request.schedule_date and request.schedule_date + relativedelta(hours=1)
            )

    @api.depends("schedule_date", "schedule_end")
    def _compute_duration(self):
        for request in self:
            if request.schedule_date and request.schedule_end:
                duration = (
                    request.schedule_end - request.schedule_date
                ).total_seconds() / 3600
                request.duration = round(duration, 2)
            else:
                request.duration = 0

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
            self.env["maintenance.team"]
            .with_company(company)
            .search(
                [("company_id", "in", [company.id, False])],
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

    @api.depends("maintenance_type")
    def _compute_recurring_maintenance(self):
        for request in self:
            if request.maintenance_type != "preventive":
                request.recurring_maintenance = False

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
        res = super().write(vals)
        if vals.get("owner_user_id") or vals.get("user_id"):
            self._add_followers()
        if closing:
            closing.activity_feedback([REQUEST_ACTIVITY_TYPE])
            closing._create_next_occurrences()
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

    def _create_next_occurrences(self):
        for request in self:
            if vals := request._prepare_next_occurrence_vals():
                request.copy(vals)

    def _prepare_next_occurrence_vals(self):
        self.check_singleton()
        if self.maintenance_type != "preventive" or not self.recurring_maintenance:
            return {}
        schedule_date = (
            self.schedule_date or fields.Datetime.now()
        ) + self._get_recurrence_delta()
        if self.repeat_type == "until" and not (
            self.repeat_until and schedule_date.date() <= self.repeat_until
        ):
            return {}
        return {
            "schedule_date": schedule_date,
            "schedule_end": schedule_date + relativedelta(hours=self.duration or 1),
            "stage_id": self._default_stage_id().id,
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
    def _read_group_stage_ids(self, stages, domain):
        """Read group customization in order to display all the stages in the
        kanban view, even if they are empty
        """
        stage_ids = stages.sudo()._search([], order=stages._order)
        return stages.browse(stage_ids)


class MaintenanceTeam(models.Model):
    _name = "maintenance.team"
    _inherit = ["mixin.mail.alias", "mixin.mail.thread"]
    _description = "Maintenance Teams"

    name = fields.Char(
        string="Team Name",
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    member_ids = fields.Many2many(
        comodel_name="res.users",
        relation="maintenance_team_users_rel",
        string="Team Members",
        domain="company_id and [('company_ids', 'in', company_id)] or []",
    )
    color = fields.Integer(string="Color Index")
    request_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="maintenance_team_id",
        copy=False,
    )
    equipment_ids = fields.One2many(
        comodel_name="maintenance.equipment",
        inverse_name="maintenance_team_id",
        copy=False,
    )

    # For the dashboard only
    todo_request_count = fields.Integer(
        string="Number of Requests",
        compute="_compute_todo_requests",
    )
    todo_request_count_date = fields.Integer(
        string="Number of Requests Scheduled",
        compute="_compute_todo_requests",
    )
    todo_request_count_high_priority = fields.Integer(
        string="Number of Requests in High Priority",
        compute="_compute_todo_requests",
    )
    todo_request_count_block = fields.Integer(
        string="Number of Requests Blocked",
        compute="_compute_todo_requests",
    )
    todo_request_count_unscheduled = fields.Integer(
        string="Number of Requests Unscheduled",
        compute="_compute_todo_requests",
    )
    alias_id = fields.Many2one(help="Email alias for this maintenance team.")

    @api.depends("request_ids.stage_id.done")
    def _compute_todo_requests(self):
        Request = self.env["maintenance.request"]
        data_by_team = defaultdict(list)
        for team, *row in Request._read_group(
            [("maintenance_team_id", "in", self.ids), *Request._get_domain_open()],
            ["maintenance_team_id", "schedule_date:year", "priority", "kanban_state"],
            ["__count"],
        ):
            data_by_team[team].append(row)
        for team in self:
            data = data_by_team[team]
            team.todo_request_count = sum(count for (_, _, _, count) in data)
            team.todo_request_count_date = sum(
                count for (schedule_date, _, _, count) in data if schedule_date
            )
            team.todo_request_count_high_priority = sum(
                count for (_, priority, _, count) in data if priority == "3"
            )
            team.todo_request_count_block = sum(
                count
                for (_, _, kanban_state, count) in data
                if kanban_state == "blocked"
            )
            team.todo_request_count_unscheduled = (
                team.todo_request_count - team.todo_request_count_date
            )

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get("maintenance.request").id
        if self.id:
            values["alias_defaults"] = defaults = self._get_alias_defaults()
            defaults["maintenance_team_id"] = self.id
        return values
