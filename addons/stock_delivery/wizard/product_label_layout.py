from odoo import models


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    def _prepare_label_values(
        self, product, barcode_value, copies, packaging, secondary_text='',
    ):
        label = super()._prepare_label_values(product, barcode_value, copies, packaging, secondary_text=secondary_text)
        label['hs_code'] = product.hs_code or ''
        return label
