
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductDocument(models.Model):
    _name = 'product.document'
    _description = "Product Document"
    _inherits = {
        'ir.attachment': 'ir_attachment_id',
    }
    _order = 'id desc'

    ir_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Related attachment",
        required=True,
        ondelete='cascade')

    active = fields.Boolean(default=True)

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        return super(
            ProductDocument,
            self.with_context(disable_product_documents_creation=True),
        ).create(vals_list)

    def copy_multi(self, default_list=None):
        if default_list is None:
            default_list = [None] * len(self)
        ir_fields = list(self.env['ir.attachment']._fields)
        for document, default in zip(self, default_list):
            ir_default = default
            if ir_default:
                ir_default = {field : default[field] for field in default if field in ir_fields}
            new_attach = document.ir_attachment_id.with_context(
                no_document=True,
                disable_product_documents_creation=True,
            ).copy_multi(default_list=[ir_default])
            default['ir_attachment_id'] = new_attach.id
        return super().copy_multi(default_list=default_list)

    def unlink(self):
        attachments = self.ir_attachment_id
        res = super().unlink()
        return res and attachments.unlink()
