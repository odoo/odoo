from odoo import _, api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_from_submitted_expense(self):
        for attachment in self:
            model = attachment.res_model
            res_id = attachment.res_id
            if model == "hr.expense" and res_id:
                expense = self.env[model].browse(res_id)
                if not expense.has_access('write'):
                    raise UserError(_("You can't delete attachments from a submitted expense."))
