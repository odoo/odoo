# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.product.controllers.product_document import ProductDocumentController


class ProductDocumentControllerECO(ProductDocumentController):
    def is_model_valid(self, res_model):
        return super().is_model_valid(res_model) or res_model == 'mrp.eco'

    def get_additional_create_params(self, **kwargs):
        super_values = super().get_additional_create_params(**kwargs)
        if kwargs.get('eco_bom'):
            return super_values | {'attached_on_mrp': 'bom'}
        return super_values
