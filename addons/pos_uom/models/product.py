from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pos_second_uom = fields.Many2one("uom.uom", "POS Second UoM", domain="[('category_id', '=', uom_category_id), ('id','!=',uom_id)]")

    @api.onchange('uom_id')
    def _onchange_id(self):
        if self.pos_second_uom and self.pos_second_uom.id == self.uom_id.id:
            raise ValidationError(
                _("Primary and Secondary units cannot be same")
            )


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields.append('pos_second_uom')
        return fields
