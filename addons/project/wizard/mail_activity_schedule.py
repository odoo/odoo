# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    task_id = fields.Many2one(
        "project.task",
        compute="_compute_task_id",
        store=False,
        readonly=False,
    )
    task_id_domain = fields.Char(
        compute="_compute_task_id_domain",
        export_string_translation=False,
    )

    @api.depends_context("log_contact_id")
    def _compute_task_id_domain(self):
        if contact := self.env["res.partner"].browse(self.env.context.get("log_contact_id")):
            all_child = self.env["res.partner"].with_context(active_test=False).search([("id", "child_of", contact.id)])
            task_id_domain = [("partner_id", "in", (contact | all_child).ids)]
        else:
            task_id_domain = []
        self.task_id_domain = task_id_domain

    def _get_res_model_fields(self):
        return {**super()._get_res_model_fields(), "project.task": "task_id"}

    def _selection_res_model(self):
        res = super()._selection_res_model()
        if self.env.user.has_group("project.group_project_user"):
            res += [("project.task", self.env._("Task"))]
        return res

    @api.depends("res_model_selection", "task_id_domain")
    def _compute_task_id(self):
        for activity in self:
            if activity.task_id or activity.res_model_selection != "project.task":
                continue
            domain = literal_eval(activity.task_id_domain)
            activity.task_id = self.env.context.get("default_task_id") or activity.env["project.task"].search(
                domain, limit=1, order="id desc",
            )
