import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    tiktok_sku = fields.Char('Tiktok SKU')
    is_tiktok = fields.Boolean('Tiktok Product', default = False)
    tiktok_description = fields.Text('Description',help="A precise description of the Product, used only for internal information purposes.")

    is_auto_stock = fields.Boolean('Auto Stock', default=False)
    is_sync_tiktok = fields.Boolean('Sync to Tiktok', default=False)
    tiktok_price = fields.Float('Price')

    tiktok_product_ids = fields.One2many('tiktok.product', 'product_tmpl_id', 'Tiktok Products')
    tiktok_product_image_ids = fields.One2many('tiktok.product.image', 'product_tmpl_id', 'Tiktok Images')

    attachment_id = fields.Many2one('ir.attachment', 'Attachments')
    upload_product_tt_image_ids = fields.Many2many('ir.attachment', 'res_tiktok_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

    _sql_constraints = [
        ('tiktok_sku_uniq', 'unique(tiktok_sku)', 'You cannot have more than one product with the same TikTok SKU!')
    ]

    @api.model
    def create(self, vals):
        context = self.env.context
        result = super(ProductTemplate, self.with_context(context)).create(vals)
        if vals.get('upload_product_tt_image_ids'):
            for x in vals.get('upload_product_tt_image_ids'):
                if x[0] == 4:
                    attachment_id = self.env['ir.attachment'].browse(x[1])
                    if attachment_id.datas:
                        self.env['tiktok.product.image'].create({
                            'image_id': x[1],
                            'image': attachment_id.datas,
                            'name': attachment_id.name,
                            'product_tmpl_id': result.id
                        })
                if x[0] == 3:
                    tiktok_img_id = self.env['tiktok.product.image'].search([('image_id','=',x[1])]).unlink()

        return result

    def write(self, vals):
        context = self.env.context
        result = super(ProductTemplate, self.with_context(context)).write(vals)
        if vals.get('upload_product_tt_image_ids'):
            for x in vals.get('upload_product_tt_image_ids'):
                if x[0] == 4:
                    attachment_id = self.env['ir.attachment'].browse(x[1])
                    if attachment_id.datas:
                        self.env['tiktok.product.image'].create({
                            'image_id': x[1],
                            'image': attachment_id.datas,
                            'name': attachment_id.name,
                            'product_tmpl_id': self.id
                        })
                if x[0] == 3:
                    tiktok_img_id = self.env['tiktok.product.image'].search([('image_id','=',x[1])]).unlink()

        return result

    def action_delete_all_tiktok_img(self):
        for dels in self:
            if dels.tiktok_product_image_ids:
                print(dels,'DELSS==')
                dels.tiktok_product_image_ids.unlink()

    def action_open_delete_confirmation_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delete Confirmation',
            'res_model': 'delete.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_name': self.name,
            },
        }

    def action_upload_image_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upload Image',
            'res_model': 'upload.image.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_name': self.name,
            },
        }

class ProductProduct(models.Model):
    _inherit = "product.product"

    tiktok_variation_sku = fields.Char('Variation SKU')
    is_sync_tiktok = fields.Boolean('Sync to Tiktok', default=False)
    tiktok_product_variant_ids = fields.One2many('tiktok.product.variant', 'product_id', 'Tiktok Product Variants')
    
    adjust_qty = fields.Float('Adjust Quantity')
    tiktok_product_var_image_ids = fields.One2many('tiktok.product.image.variant', 'product_id', 'Tiktok Variant Images')

    attachment_id = fields.Many2one('ir.attachment', 'Attachments')
    upload_product_var_tt_image_ids = fields.Many2many('ir.attachment', 'res_tiktok_var_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

    _sql_constraints = [
        ('tiktok_variation_sku_uniq', 'unique(tiktok_variation_sku)', 'You cannot have more than one product with the same TikTok Variant SKU!')
    ]

    @api.model
    def create(self, vals):
        context = self.env.context
        result = super(ProductProduct, self.with_context(context)).create(vals)
        if vals.get('upload_product_var_tt_image_ids'):
            for x in vals.get('upload_product_var_tt_image_ids'):
                if x[0] == 4:
                    attachment_id = self.env['ir.attachment'].browse(x[1])
                    if attachment_id.datas:
                        self.env['tiktok.product.image.variant'].create({
                            'image_id': x[1],
                            'image': attachment_id.datas,
                            'name': attachment_id.name,
                            'product_id': result.id
                        })
                if x[0] == 3:
                    tiktok_img_id = self.env['tiktok.product.image.variant'].search([('image_id','=',x[1])]).unlink()

        return result

    def write(self, vals):
        context = self.env.context
        result = super(ProductProduct, self.with_context(context)).write(vals)
        if vals.get('upload_product_var_tt_image_ids'):
            for x in vals.get('upload_product_var_tt_image_ids'):
                if x[0] == 4:
                    attachment_id = self.env['ir.attachment'].browse(x[1])
                    if attachment_id.datas:
                        self.env['tiktok.product.image.variant'].create({
                            'image_id': x[1],
                            'image': attachment_id.datas,
                            'name': attachment_id.name,
                            'product_id': self.id
                        })
                if x[0] == 3:
                    tiktok_img_id = self.env['tiktok.product.image.variant'].search([('image_id','=',x[1])]).unlink()

        return result

    def action_delete_all_tiktok_var_img(self):
        for dels in self:
            if dels.tiktok_product_var_image_ids:
                dels.tiktok_product_var_image_ids.unlink()

    def action_open_delete_confirmation_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delete Confirmation',
            'res_model': 'delete.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_name': self.name,
            },
        }