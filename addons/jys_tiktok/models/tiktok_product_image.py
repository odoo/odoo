from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
from PIL import Image
import io

class TiktokProductImage(models.Model):
    _name = 'tiktok.product.image'
    _description = 'Tiktok Product Image'

    name = fields.Char(string="Description")
    image = fields.Binary(string="Image", attachment=True)
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")
    image_id = fields.Integer('Image ID')
    image_ids = fields.One2many('tiktok.product.image.variant','product_image_id','Variant Images')
    uri = fields.Char('URI')

    def is_valid_image(self, vals):
        supported_formats = ['JPEG', 'JPG', 'PNG']
        
        min_pixels = 300
        max_pixels = 20000
        
        max_file_size = 5 * 1024 * 1024 #5MB
        
        try:
            image_data = base64.b64decode(vals['image'])
            image_size = len(image_data)
            
            if image_size > max_file_size:
                return False, "File size exceeds 5MB."
            
            image = Image.open(io.BytesIO(image_data))

            if image.format not in supported_formats:
                return False, "Unsupported image format. Must be JPG, JPEG, or PNG."
            
            width, height = image.size
            if not (min_pixels <= width <= max_pixels and min_pixels <= height <= max_pixels):
                return False, "Image dimensions out of range. Must be between 300x300 and 20000x20000 pixels."
            
            return True, "Image is valid."
        
        except Exception as e:
            return False, f"An error occurred: {str(e)}" 

    @api.model
    def create(self, vals):
        context = self.env.context
        if vals.get('name'):
            image = vals.get('name')
            image_format = image.split('.')
            if image_format[-1] not in ['jpeg','jpg','png']:
                raise UserError(_('[%s], Unsupported image format. Must be JPG, JPEG, or PNG.')%(vals.get('name')))

            check = self.is_valid_image(vals)
            if not check[0]:
                raise UserError(_('[%s], %s')%(vals.get('name'), check[1]))
        return super(TiktokProductImage, self.with_context(context)).create(vals)

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
    product_image_id = fields.Many2one('tiktok.product.image','Product Image')
    product_id = fields.Many2one('product.product', string="Product Variant")
    image_id = fields.Integer('Image ID')
    uri = fields.Char('URI')

    def is_valid_image(self, vals):
        supported_formats = ['JPEG', 'JPG', 'PNG']
        
        min_pixels = 300
        max_pixels = 20000
        
        max_file_size = 5 * 1024 * 1024 #5MB
        
        try:
            image_data = base64.b64decode(vals['image'])
            image_size = len(image_data)
            
            if image_size > max_file_size:
                return False, "File size exceeds 5MB."
            
            image = Image.open(io.BytesIO(image_data))
            
            if image.format not in supported_formats:
                return False, "Unsupported image format. Must be JPG, JPEG, or PNG."
            
            width, height = image.size
            if not (min_pixels <= width <= max_pixels and min_pixels <= height <= max_pixels):
                return False, "Image dimensions out of range. Must be between 300x300 and 20000x20000 pixels."
            
            return True, "Image is valid."
        
        except Exception as e:
            return False, f"An error occurred: {str(e)}" 

    @api.model
    def create(self, vals):
        context = self.env.context
        if vals.get('name'):
            image = vals.get('name')
            image_format = image.split('.')
            if image_format[-1] not in ['jpeg','jpg','png']:
                raise UserError(_('[%s], Unsupported image format. Must be JPG, JPEG, or PNG.')%(vals.get('name')))

            check = self.is_valid_image(vals)
            if not check[0]:
                raise UserError(_('[%s], %s')%(vals.get('name'), check[1]))
        return super(TiktokProductImageVariant, self.with_context(context)).create(vals)

    def unlink(self):
        for dels in self:
            attachment_id = self.env['ir.attachment'].browse(dels.image_id)
            if attachment_id.datas:
                attachment_id.unlink()
        return super(TiktokProductImageVariant, self).unlink()