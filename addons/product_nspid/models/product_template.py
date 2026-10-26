from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    manufacturing_pid = fields.Char('Manufacturing PID', compute="_compute_manufacturing_pid", inverse="_inverse_manufacturing_pid", help="The manufacturer's own product reference that does not conform to an internationally recognised standard (e.g., a proprietary model code). Supplements the merchant identifier for shipping.")

    def _compute_manufacturing_pid(self):
        for template in self:
            if template.product_variant_count == 1:
                template.manufacturing_pid = template.product_variant_id.manufacturing_pid
            else:
                template.manufacturing_pid = False

    def _inverse_manufacturing_pid(self):
        for template in self:
            if template.product_variant_count == 1:
                template.product_variant_id.manufacturing_pid = template.manufacturing_pid
