from odoo import models, api


class IrAttachment(models.Model):
    _name = "ir.attachment"
    _inherit = ["ir.attachment", "pos.load.mixin"]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'datas']
