from odoo import _, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = "project.project"

    def action_view_deliveries(self):
        self.check_singleton()
        return self._get_picking_action(_("From WH"), "outgoing")

    def action_view_receipts(self):
        self.check_singleton()
        return self._get_picking_action(_("To WH"), "incoming")

    def action_view_all_pickings(self):
        self.check_singleton()
        return self._get_picking_action(_("Stock Moves"))

    def _get_picking_action(self, action_name, picking_type=None):
        _debug.logic("project_picking_action", projects=self, action=action_name)
        domain = Domain("project_id", "=", self.id)
        context = {"default_project_id": self.id}
        if picking_type:
            domain &= Domain("picking_type_id.code", "=", picking_type)
            context["restricted_picking_type_code"] = picking_type
            if picking_type == "outgoing":
                context["default_partner_id"] = self.partner_id.id
        view_mode = "list,kanban,form,calendar"
        if picking_type != "outgoing":
            view_mode += ",activity"
        return {
            "name": action_name,
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": view_mode,
            "domain": domain,
            "context": context,
            "help": self.env["ir.ui.view"]._render_template(
                "stock.help_message_template",
                {
                    "picking_type_code": picking_type,
                },
            ),
        }
