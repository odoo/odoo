from odoo import models, api, _
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_action(self):
        action_report_quotation = self.env["ir.actions.actions"]._for_xml_id("purchase.report_purchase_quotation")
        if action_report_quotation.get("id") in self.ids:
            raise UserError(_("You cannot delete %s", action_report_quotation.get("name")))
