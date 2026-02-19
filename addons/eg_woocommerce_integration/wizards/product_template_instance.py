import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplateInstance(models.TransientModel):
    _name = 'product.template.instance'

    instance_id = fields.Many2one(comodel_name='eg.ecom.instance', string="Instance")

    def export_in_woo_product_template(self):
        self.env['product.template'].woo_odoo_product_template_process(instance_id=self.instance_id)
