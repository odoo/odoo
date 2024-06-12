from odoo import models, fields

class ShopeeProductImage(models.Model):
    _name = 'shopee.product.image'
    _description = 'Shopee Product Image'

    name = fields.Char(string="Description")
    image = fields.Binary(string="Image", attachment=True)
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")
    image_id = fields.Integer('Image ID')

    def unlink(self):
        for dels in self:
            attachment_id = self.env['ir.attachment'].browse(dels.image_id)
            print(attachment_id,'attachment_id===')
            if attachment_id.datas:
                attachment_id.unlink()
        return super(ShopeeProductImage, self).unlink()

class ShopeeProductImageVariant(models.Model):
    _name = 'shopee.product.image.variant'
    _description = 'Shopee Product Image Variant'

    name = fields.Char(string="Description")
    image = fields.Binary(string="Image", attachment=True)
    product_id = fields.Many2one('product.product', string="Product Variant")
    image_id = fields.Integer('Image ID')

    def unlink(self):
        for dels in self:
            attachment_id = self.env['ir.attachment'].browse(dels.image_id)
            print(attachment_id,'attachment_id var===')
            if attachment_id.datas:
                attachment_id.unlink()
        return super(ShopeeProductImageVariant, self).unlink()