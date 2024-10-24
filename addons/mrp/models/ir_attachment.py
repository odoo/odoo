# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _name = "ir.attachment"
    _inherit = "ir.attachment"

    def _pre_create_check(self, vals_list):
        for vals in vals_list:
            if vals.get('res_model') == 'mrp.bom':
                bom = self.env['mrp.bom'].browse(vals['res_id'])
                vals['res_model'] = bom.product_id._name if bom.product_id else bom.product_tmpl_id._name
                vals['res_id'] = bom.product_id.id if bom.product_id else bom.product_tmpl_id.id
        return vals_list

    def _create_product_document(self, product_attachments):
        self.env['product.document'].sudo().create(
                    {
                        'ir_attachment_id': attachment.id,
                        'attached_on_mrp': 'bom'
                    } for attachment in product_attachments
                )
