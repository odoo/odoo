from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _get_product_document_models(self):
        res = super()._get_product_document_models()
        res.append('mrp.bom')
        return res
