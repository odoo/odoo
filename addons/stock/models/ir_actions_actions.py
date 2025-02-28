from odoo import api, models, _
from odoo.exceptions import UserError

class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_action(self):
        """ Prevents deletion of the Stock Picking action."""
        action_report_picking = self.env["ir.actions.actions"]._for_xml_id("stock.action_report_picking")
        if action_report_picking.get("id") in self.ids:
                raise UserError(_("You cannot delete %s", action_report_picking.get("name")))
