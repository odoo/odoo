from odoo import models
from odoo.osv import expression


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _get_spreadsheet_attachment_domain(self):
        domain = super()._get_spreadsheet_attachment_domain()
        return expression.OR([domain, [
            ("res_model", "=", "spreadsheet.dashboard"),
            ("res_field", "=", "data")
        ]])
