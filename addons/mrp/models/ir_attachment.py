from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for attachment in attachments:
            if attachment.res_model == 'mrp.bom' and attachment.res_id:
                bom = self.env['mrp.bom'].browse(attachment.res_id)
                if bom.exists():
                    if bom.product_id:
                        target_model = 'product.product'
                        target_id = bom.product_id.id
                    else:
                        target_model = 'product.template'
                        target_id = bom.product_tmpl_id.id
                    attachment.copy({
                        'res_model': target_model,
                        'res_id': target_id,
                    })
        return attachments

    @api.ondelete(at_uninstall=False)
    def _unlink_bom_copied_attachments(self):
        attachments_to_delete = self.env['ir.attachment']
        for attachment in self:
            if attachment.res_model == 'mrp.bom' and attachment.res_id:
                bom = self.env['mrp.bom'].browse(attachment.res_id)
                if bom.exists():
                    target_model = 'product.product' if bom.product_id else 'product.template'
                    target_id = bom.product_id.id if bom.product_id else bom.product_tmpl_id.id
                    domain = [
                        ('res_model', '=', target_model),
                        ('res_id', '=', target_id),
                        ('name', '=', attachment.name),
                        ('checksum', '=', attachment.checksum),
                    ]
                    if attachments_to_delete:
                        domain.append(('id', 'not in', attachments_to_delete.ids))
                    copied_attachments = self.env['ir.attachment'].search(domain, limit=1)
                    attachments_to_delete |= copied_attachments
        if attachments_to_delete:
            attachments_to_delete.unlink()
