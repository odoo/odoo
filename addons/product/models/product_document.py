
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductDocument(models.Model):
    _name = 'product.document'
    _description = "Product Document"
    _inherits = {
        'ir.attachment': 'ir_attachment_id',
    }

    ir_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Related attachment",
        required=True,
        ondelete='cascade')

    active = fields.Boolean(default=True)

    #=== CRUD METHODS ===#

    def copy(self, default=None):
        ir_default = default
        if ir_default:
            ir_fields = list(self.env['ir.attachment']._fields)
            ir_default = {field : default[field] for field in default if field in ir_fields}
        new_attach = self.ir_attachment_id.with_context(no_document=True).copy(ir_default)
        return super().copy(dict(default, ir_attachment_id=new_attach.id))

    def unlink(self):
        self.ir_attachment_id.unlink()
        return super().unlink()
