from odoo import models


class ProductImageData(models.Model):
    _inherit = "html_editor.image.data"
    _description = 'Product Image Data'

    def _get_image_data_res_info(self, res_model, res_id, res_field):
        if res_model == 'product.product' and res_field == 'image_1920':
            product_record = self.env['product.product'].browse(res_id)
            res_field_variant = 'image_variant_1920'
            if product_record[res_field_variant]:
                # The product has a variant. Take the image data of the product
                # image variant.
                return super()._get_image_data_res_info(res_model, res_id, res_field_variant)
            # The product does not have variant. Take the image data of the
            # template image.
            return super()._get_image_data_res_info('product.template', product_record.product_tmpl_id.id, res_field)
        return super()._get_image_data_res_info(res_model, res_id, res_field)

    def _update_image_data_res_info(self, res_model, res_id, res_field):
        if res_model == 'product.product' and res_field == 'image_1920':
            product_record = self.env['product.product'].browse(res_id)
            if (
                # We are trying to add a field to the variant, but the template
                # field is not set, write on the template instead.
                not product_record.product_tmpl_id[res_field]
                # There is only one variant, always write on the template
                or product_record.search_count([
                    ('product_tmpl_id', '=', product_record.product_tmpl_id.id),
                    ('active', '=', True),
                ]) <= 1
            ):
                # Write on the template
                return super()._update_image_data_res_info('product.template', product_record.product_tmpl_id.id, res_field)
            return super()._update_image_data_res_info(res_model, res_id, 'image_variant_1920')
        return super()._update_image_data_res_info(res_model, res_id, res_field)
