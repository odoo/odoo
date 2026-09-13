from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import debug_log as dbg


class ProjectPhase(models.Model):
    _name = "project.phase"
    _description = "Project Phase"
    _inherit = ["mixin.project.pm"]
    _order = "sequence, id"

    active = fields.Boolean(
        export_string_translation=False,
        default=True,
    )
    sequence = fields.Integer(
        export_string_translation=False,
        default=50,
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        domain=[("model", "=", "project.project")],
        help="Email sent automatically when a project enters this phase.",
    )
    fold = fields.Boolean(
        string="Folded",
        help="Folded phases are shown collapsed in Kanban and List views. "
        "Projects in a folded phase are considered closed.",
    )
    company_id = fields.Many2one(comodel_name="res.company")
    color = fields.Integer(export_string_translation=False)

    @api.constrains("mail_template_id")
    def _check_mail_template_model(self) -> None:
        for phase in self:
            template = phase.mail_template_id
            if template and template.model != "project.project":
                raise ValidationError(
                    _(
                        "The email template %(template)s is defined on %(model)s, but a "
                        "phase email is sent about a project. Choose a template whose "
                        "model is Project.",
                        template=template.display_name,
                        model=template.model,
                    )
                )

    def action_open_delete_wizard(self, stage_view: bool = False) -> dict[str, Any]:
        dbg.lifecycle.debug(
            "project.phase.action_open_delete_wizard %s (stage_view=%s)",
            dbg.rec(self),
            stage_view,
        )
        wizard = self.env["project.phase.delete.wizard"].create({"phase_ids": self.ids})
        context = dict(self.env.context, stage_view=stage_view)
        return {
            "name": _("Delete Phase"),
            "view_mode": "form",
            "res_model": "project.phase.delete.wizard",
            "views": [
                (
                    self.env.ref("project.view_project_phase_delete_wizard").id,
                    "form",
                )
            ],
            "type": "ir.actions.act_window",
            "res_id": wizard.id,
            "target": "new",
            "context": context,
        }

    @dbg.timed
    def write(self, vals: dict) -> bool:
        dbg.lifecycle.debug(
            "project.phase.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if vals.get("company_id"):
            project = self.env["project.project"].search(
                [
                    "&",
                    ("phase_id", "in", self.ids),
                    ("company_id", "!=", vals["company_id"]),
                ],
                limit=1,
            )
            if project:
                company = self.env["res.company"].browse(vals["company_id"])
                raise UserError(
                    _(
                        "You cannot switch this phase to %(company_name)s because it "
                        "currently includes projects linked to %(project_company_name)s.",
                        company_name=company.name,
                        project_company_name=project.company_id.name or _("no company"),
                    )
                )
        if "active" in vals and not vals["active"]:
            projects = self.env["project.project"].search(
                [("phase_id", "in", self.ids)]
            )
            dbg.pipeline.debug(
                "[phase:%s] archive -> archiving projects %s",
                dbg.rec(self),
                dbg.rec(projects),
            )
            projects.write({"active": False})
        return super().write(vals)
