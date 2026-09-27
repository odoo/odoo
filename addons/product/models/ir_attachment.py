# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        """Create product.document for attachments added in products chatters"""
        attachments = super().create(vals_list)
        if not self.env.context.get('disable_product_documents_creation'):
            product_attachments = attachments.filtered(
                lambda attachment:
                    attachment.res_model in ('product.product', 'product.template')
                    and not attachment.res_field
            )
            if product_attachments:
                self.env['product.document'].sudo().create([
                    {
                        'ir_attachment_id': attachment.id
                    }
                    for attachment in product_attachments
                ])
        return attachments
