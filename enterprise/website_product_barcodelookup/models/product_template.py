from odoo import api, models, Command


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _update_product_by_barcodelookup(self, product, barcode_lookup_data):
        product.ensure_one()
        description = super()._update_product_by_barcodelookup(product, barcode_lookup_data)
        if not product.description_ecommerce:
            product.description_ecommerce = description
        return description

    def _set_lookup_image(self, product, img):
        image = super()._set_lookup_image(product, img)
        if image is not True:
            self.product_template_image_ids = [Command.create({
                'name': product.name,
                'image_1920': image,
            })]
        return image
