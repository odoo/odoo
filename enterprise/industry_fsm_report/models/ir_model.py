from odoo import api, models
from odoo.tools.sql import column_exists


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.ondelete(at_uninstall=True)
    def _unlink_if_uninstalling(self):
        # If module 'worksheet' is also being uninstalled, then column 'model_id'
        # has already been dropped. That's simply because ir.model.fields records
        # are deleted before ir.model records. In that situation, the call to
        # search() below simply crashes because of the missing column.
        if column_exists(self.env.cr, "worksheet_template", "model_id"):
            self.env["worksheet.template"].with_context(active_test=False).search(
                [("model_id", "in", self.ids)]
            ).unlink()
