from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


class ProjectRetrospective(models.Model):
    _name = "project.retrospective"
    _description = "Project Retrospective"
    _order = "date desc, id desc"
    _inherit = ["mixin.mail.thread"]

    name = fields.Char(
        string="Title",
        required=True,
        tracking=True,
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        index=True,
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(
        default=fields.Date.today,
        required=True,
    )
    facilitator_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
    )
    went_well = fields.Html(
        string="What Went Well",
        help="Practices and decisions that should be repeated.",
    )
    to_improve = fields.Html(
        string="What Needs Improvement",
        help="Areas where changes would improve outcomes.",
    )
    action_ids = fields.One2many(
        comodel_name="project.retrospective.action",
        inverse_name="retrospective_id",
        string="Action Items",
    )
    action_count = fields.Count(
        count_of="action_ids",
        string="Actions",
        export_string_translation=False,
    )
    open_action_count = fields.Integer(
        string="Open Actions",
        export_string_translation=False,
        compute="_compute_open_action_count",
    )
    previous_id = fields.Many2one(
        comodel_name="project.retrospective",
        string="Previous Retrospective",
        help="Link to the previous retrospective for action carry-forward.",
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done")],
        default="draft",
        required=True,
        tracking=True,
    )

    @api.depends("action_ids.state")
    def _compute_open_action_count(self) -> None:
        for retro in self:
            retro.open_action_count = len(
                retro.action_ids.filtered(lambda a: a.state in ("open", "in_progress"))
            )

    @api.constrains("previous_id")
    def _check_previous_no_cycle(self) -> None:
        if self._has_cycle("previous_id"):
            raise ValidationError(
                self.env._(
                    "A retrospective cannot be its own predecessor "
                    "(circular 'Previous Retrospective' link)."
                )
            )

    @dbg.timed
    def action_carry_forward(self) -> None:
        self.check_singleton()
        if not self.previous_id:
            dbg.logic.debug(
                "project.retrospective.action_carry_forward %s: no previous_id",
                dbg.rec(self),
            )
            return
        already_carried = set(self.action_ids.mapped("carried_from_id").ids)
        open_actions = self.previous_id.action_ids.filtered(
            lambda a: a.state in ("open", "in_progress") and a.id not in already_carried
        )
        dbg.lifecycle.debug(
            "project.retrospective.action_carry_forward %s: from %s, %d already "
            "carried, carrying %s",
            dbg.rec(self),
            self.previous_id.id,
            len(already_carried),
            dbg.rec(open_actions),
        )
        vals_list = [
            {
                **copy_vals,
                "retrospective_id": self.id,
                "carried_from_id": action.id,
            }
            for action, copy_vals in zip(
                open_actions, open_actions.copy_data(), strict=True
            )
        ]
        self.env["project.retrospective.action"].create(vals_list)


class ProjectRetrospectiveAction(models.Model):
    _name = "project.retrospective.action"
    _description = "Retrospective Action Item"
    _order = "state_order, date_due, id"

    name = fields.Char(
        string="Action",
        required=True,
    )
    retrospective_id = fields.Many2one(
        comodel_name="project.retrospective",
        index=True,
        required=True,
        ondelete="cascade",
    )
    project_id = fields.Many2one(
        related="retrospective_id.project_id",
    )
    owner_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
    )
    date_due = fields.Date(string="Due Date")
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("dropped", "Dropped"),
        ],
        default="open",
        required=True,
    )
    state_order = fields.Integer(
        export_string_translation=False,
        compute="_compute_state_order",
        store=True,
        help="Sort key: outstanding actions first. Ordering by ``state`` "
        "directly sorts on the stored keys, which puts Done and Dropped "
        "above the open items this list exists to surface.",
    )
    resolution_note = fields.Text(help="How was this action resolved?")
    carried_from_id = fields.Many2one(
        comodel_name="project.retrospective.action",
        help="If this action was carried forward from a previous retrospective.",
    )
    category = fields.Selection(
        selection=[
            ("estimation", "Estimation"),
            ("scope", "Scope"),
            ("communication", "Communication"),
            ("technical", "Technical"),
            ("process", "Process"),
            ("team", "Team"),
            ("tooling", "Tooling"),
        ]
    )

    _STATE_ORDER = {"open": 0, "in_progress": 1, "done": 2, "dropped": 3}

    @api.depends("state")
    def _compute_state_order(self) -> None:
        for action in self:
            action.state_order = self._STATE_ORDER.get(action.state, 99)
