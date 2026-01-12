# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class FSTestConnection(models.TransientModel):
    _name = "fs.test.connection"
    _description = "FS Test Connection Wizard"

    def _get_check_connection_method_selection(self):
        return self.env["fs.storage"]._get_check_connection_method_selection()

    storage_id = fields.Many2one("fs.storage")
    check_connection_method = fields.Selection(
        selection="_get_check_connection_method_selection",
        required=True,
    )

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        res["storage_id"] = self.env.context.get("active_id", False)
        return res

    def action_test_config(self):
        return self.storage_id._test_config(self.check_connection_method)
