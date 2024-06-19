from odoo import models, fields

class TiktokProductImage(models.Model):
    _name = 'tiktok.product.image'
    _description = 'Tiktok Product Image'

    name = fields.Char(string="Description")
    image = fields.Binary(string="Image", attachment=True)
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")
    image_id = fields.Integer('Image ID')

    def unlink(self):
        for dels in self:
            attachment_id = self.env['ir.attachment'].browse(dels.image_id)
            if attachment_id.datas:
                attachment_id.unlink()
        return super(TiktokProductImage, self).unlink()

class TiktokProductImageVariant(models.Model):
    _name = 'tiktok.product.image.variant'
    _description = 'Tiktok Product Image Variant'

    name = fields.Char(string="Description")
    image = fields.Binary(string="Image", attachment=True)
    product_id = fields.Many2one('product.product', string="Product Variant")
    image_id = fields.Integer('Image ID')

    def unlink(self):
        for dels in self:
            attachment_id = self.env['ir.attachment'].browse(dels.image_id)
            if attachment_id.datas:
                attachment_id.unlink()
        return super(TiktokProductImageVariant, self).unlink()