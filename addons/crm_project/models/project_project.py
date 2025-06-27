# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.tools.translate import _


class ProjectProject(models.Model):
    _inherit = "project.project"

    lead_id = fields.Many2one("crm.lead", index=True, help="The lead associated with this project.")

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        updates = {}
        if "default_lead_id" in self.env.context:
            lead_id = self.env.context.get("default_lead_id")
            lead = self.env["crm.lead"].browse(lead_id)
            partner_id = lead.partner_id.id if lead else False
            name = lead.name if lead else ""
            updates.update({
                "name": _("Project for Lead: %(lead_name)s", lead_name=name),
                "partner_id": partner_id,
            })
            if "allow_billable" in fields_list:
                updates.update({"allow_billable": True})
        defaults.update(updates)
        return defaults

    def _log_success_create(self, project):
        """Log the creation of a project linked to a lead."""
        project.lead_id.message_post_with_source(
            "crm_project.project_creation",
            render_values={"created_record": project, "message": _("Project created")},
            subtype_xmlid="mail.mt_note",
            message_type="notification",
        )

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        for project in projects.filtered("lead_id"):
            self._log_success_create(project)
        return projects

    def success_notification_popup(self):
        """Show a success notification popup when a project is created from a lead."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Project Created"),
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
