from odoo import fields, models


class PosCategory(models.Model):
    _inherit = "pos.category"

    pos_config_ids = fields.Many2many(
        comodel_name="pos.config",
        string="Linked PoS Configurations",
    )

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_128", "image_512"]:
            return True
        return super()._can_return_content(field_name, access_token)
