import typing
from datetime import date
from typing import Literal

from odoo import _, api, exceptions, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .mail_template import MailTemplate
    from odoo.addons.bus.models.res_users import ResUsers

_debug = DebugLog(__name__)


class MailActivityType(models.Model):
    _name = "mail.activity.type"
    _inherit = ["mixin.delay"]
    _description = "Activity Type"
    _order = "sequence, id"
    _rec_name = "name"

    name = fields.Char(
        translate=True,
        required=True,
    )
    summary = fields.Char(
        string="Default Summary",
        translate=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    create_uid: ResUsers = fields.Many2one(
        comodel_name="res.users",
        index=True,
    )
    delay_count = fields.Integer(
        string="Schedule",
        help="Number of days/week/month before executing the action. It allows to plan the action deadline.",
    )
    delay_label = fields.Char(compute="_compute_delay_label")
    delay_from = fields.Selection(
        selection=[
            ("current_date", "after previous activity completion date"),
            ("previous_activity", "after previous activity deadline"),
        ],
        string="Delay Type",
        default="previous_activity",
        required=True,
        help="Type of delay",
    )
    icon = fields.Char(help="Font awesome icon e.g. fa-tasks")
    decoration_type = fields.Selection(
        selection=[("warning", "Alert"), ("danger", "Error")],
        help="Change the background color of the related activities of this type.",
    )
    res_model = fields.Selection(
        selection=lambda self: self.env["mail.activity"]._selection_activity_models(),
        string="Model",
        help="Specify a model if the activity should be specific to a model"
        " and not available when managing activities for other models.",
    )
    triggered_next_type_id: MailActivityType = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Trigger",
        compute="_compute_triggered_next_type_id",
        inverse="_inverse_triggered_next_type_id",
        store=True,
        readonly=False,
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]",
        ondelete="restrict",
        help="Automatically schedule this activity once the current one is marked as done.",
    )
    chaining_type = fields.Selection(
        selection=[
            ("suggest", "Suggest Next Activity"),
            ("trigger", "Trigger Next Activity"),
        ],
        default="suggest",
        required=True,
    )
    suggested_next_type_ids: MailActivityType = fields.Many2many(
        comodel_name="mail.activity.type",
        relation="mail_activity_rel",
        column1="activity_id",
        column2="recommended_id",
        string="Suggest",
        compute="_compute_suggested_next_type_ids",
        inverse="_inverse_suggested_next_type_ids",
        store=True,
        readonly=False,
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]",
        help="Suggest these activities once the current one is marked as done.",
    )
    previous_type_ids: MailActivityType = fields.Many2many(
        comodel_name="mail.activity.type",
        relation="mail_activity_rel",
        column1="recommended_id",
        column2="activity_id",
        string="Preceding Activities",
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]",
    )
    category = fields.Selection(
        selection=[
            ("default", "None"),
            ("upload_file", "Upload Document"),
            ("phonecall", "Phonecall"),
        ],
        string="Action",
        default="default",
        help="Actions may trigger specific behavior like opening calendar view or automatically mark as done when a document is uploaded",
    )
    mail_template_ids: MailTemplate = fields.Many2many(
        comodel_name="mail.template",
        string="Email templates",
    )
    default_user_id: ResUsers = fields.Many2one(comodel_name="res.users")
    default_note = fields.Html(translate=True)

    @api.constrains("res_model")
    def _check_activity_type_res_model(self) -> None:
        self.env["mail.activity.plan.template"].search(
            [("activity_type_id", "in", self.ids)]
        )._check_activity_type_res_model()

    @api.onchange("res_model")
    def _onchange_res_model(self) -> None:
        self.mail_template_ids = self.sudo().mail_template_ids.filtered(
            lambda template: template.model_id.model == self.res_model
        )

    @api.depends_context("lang")
    @api.depends("delay_unit", "delay_count")
    def _compute_delay_label(self) -> None:
        selection_description_values = {
            e[0]: e[1]
            for e in self._fields["delay_unit"]._description_selection(self.env)
        }
        for activity_type in self:
            unit = selection_description_values[activity_type.delay_unit]
            activity_type.delay_label = "%s %s" % (activity_type.delay_count, unit)

    @api.depends("chaining_type")
    def _compute_suggested_next_type_ids(self) -> None:
        for activity_type in self:
            if activity_type.chaining_type == "trigger":
                activity_type.suggested_next_type_ids = False

    def _inverse_suggested_next_type_ids(self) -> None:
        for activity_type in self:
            if activity_type.suggested_next_type_ids:
                activity_type.chaining_type = "suggest"

    @api.depends("chaining_type")
    def _compute_triggered_next_type_id(self) -> None:
        for activity_type in self:
            if activity_type.chaining_type == "suggest":
                activity_type.triggered_next_type_id = False

    def _inverse_triggered_next_type_id(self) -> None:
        for activity_type in self:
            if activity_type.triggered_next_type_id:
                activity_type.chaining_type = "trigger"
            else:
                activity_type.chaining_type = "suggest"

    def write(self, vals: ValuesType) -> Literal[True]:
        if "res_model" in vals:
            xmlid_to_model = {
                xmlid: info["res_model"]
                for xmlid, info in self._get_model_info_by_xmlid().items()
            }
            modified = self.browse()
            for xml_id, model in xmlid_to_model.items():
                activity_type = self.env.ref(xml_id, raise_if_not_found=False)
                if (
                    activity_type
                    and (vals["res_model"] or False) != (model or False)
                    and activity_type in self
                ):
                    modified += activity_type
            if modified:
                _debug.logic(
                    "write_refused", types=modified.ids, reason="res_model_protected"
                )
                raise exceptions.UserError(
                    _(
                        "You cannot modify %(activities_names)s target model as they are are required in various apps.",
                        activities_names=", ".join(act.name for act in modified),
                    )
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_todo(self) -> None:
        master_data = self.browse()
        for xml_id in [
            xmlid
            for xmlid, info in self._get_model_info_by_xmlid().items()
            if info["unlink"] is False
        ]:
            activity_type = self.env.ref(xml_id, raise_if_not_found=False)
            if activity_type and activity_type in self:
                master_data += activity_type
        if master_data:
            raise exceptions.UserError(
                _(
                    "You cannot delete %(activity_names)s as it is required in various apps.",
                    activity_names=", ".join(act.name for act in master_data),
                )
            )

    def action_archive(self) -> bool:
        if self.env.ref("mail.mail_activity_data_todo") in self:
            raise UserError(
                _(
                    "The 'To-Do' activity type is used to create reminders from the top bar menu and the command palette. Consequently, it cannot be archived or deleted."
                )
            )
        return super().action_archive()

    def unlink(self) -> Literal[True]:
        todo_type = self.env.ref("mail.mail_activity_data_todo")
        orphaned = (
            self.env["mail.activity"]
            .sudo()
            .with_context(active_test=False)
            .search([("activity_type_id", "in", self.ids)])
        )
        _debug.lifecycle("unlink", types=self.ids, activities_retyped=len(orphaned))
        orphaned.write(
            {
                "activity_type_id": todo_type.id,
            }
        )
        return super().unlink()

    def _get_date_deadline(self, user: ResUsers | None = None) -> date:
        self.check_singleton()
        if self.delay_from == "previous_activity" and self.env.context.get(
            "activity_previous_deadline"
        ):
            base = fields.Date.to_date(
                self.env.context.get("activity_previous_deadline")
            )
            by = "previous_activity"
        else:
            base = self.env["mail.activity"]._today_for(user)
            by = "today"
        _debug.logic(
            "deadline_computed",
            activity_type=self.id,
            by=by,
            base=base,
            delay=str(self._get_delay_delta()),
        )
        return base + self._get_delay_delta()

    @api.model
    def _get_model_info_by_xmlid(self) -> dict:
        return {
            "mail.mail_activity_data_call": {"res_model": False, "unlink": False},
            "mail.mail_activity_data_meeting": {"res_model": False, "unlink": False},
            "mail.mail_activity_data_todo": {"res_model": False, "unlink": False},
            "mail.mail_activity_data_upload_document": {
                "res_model": False,
                "unlink": True,
            },
            "mail.mail_activity_data_warning": {"res_model": False, "unlink": True},
        }
