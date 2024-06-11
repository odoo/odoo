import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    tiktok_sku = fields.Char('Tiktok SKU')
    is_tiktok = fields.Boolean('Tiktok Product', default = False)

    package_length = fields.Integer('Package Length (cm)')
    package_width = fields.Integer('Package Width (cm)')
    package_height = fields.Integer('Package Height (cm)')
    days_to_ship = fields.Integer('Days to Ship', default=2)
    
    is_pre_order = fields.Boolean('Pre-order', default=False)
    is_auto_stock = fields.Boolean('Auto Stock', default=False)
    is_sync_tiktok = fields.Boolean('Sync to Tiktok', default=False)

    tiktok_product_ids = fields.One2many('tiktok.product', 'product_tmpl_id', 'Tiktok Products')
    tiktok_product_image_ids = fields.One2many('tiktok.product.image', 'product_tmpl_id', 'Tiktok Images')

    attachment_id = fields.Many2one('ir.attachment', 'Attachments')
    upload_product_image_ids = fields.Many2many('ir.attachment', 'res_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

    @api.model
    def create(self, vals):
        context = self.env.context
        print(self,'SELF = = = = =C\n',vals)
        result = super(ProductTemplate, self.with_context(context)).create(vals)
        if vals.get('upload_product_image_ids'):
            for x in vals.get('upload_product_image_ids'):
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
                    # attachment_id = self.env['ir.attachment'].browse(x[1]).unlink()
                    # if attachment_id.datas:
                    #     attachment_id.unlink()

        return result

    def write(self, vals):
        context = self.env.context
        print(self,'SELF = = = = =W\n',vals)
        result = super(ProductTemplate, self.with_context(context)).write(vals)
        if vals.get('upload_product_image_ids'):
            for x in vals.get('upload_product_image_ids'):
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
                    # attachment_id = self.env['ir.attachment'].browse(x[1])
                    # if attachment_id.datas:
                    #     attachment_id.unlink()

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

class ProductProduct(models.Model):
    _inherit = "product.product"

    variation_sku = fields.Char('Variation SKU')
    is_sync_tiktok = fields.Boolean('Sync to Tiktok', default=False)
    tiktok_product_variant_ids = fields.One2many('tiktok.product.variant', 'product_id', 'Tiktok Product Variants')
    
    adjust_qty = fields.Float('Adjust Quantity')
    tiktok_product_var_image_ids = fields.One2many('tiktok.product.image.variant', 'product_id', 'Tiktok Variant Images')

    attachment_id = fields.Many2one('ir.attachment', 'Attachments')
    upload_product_var_image_ids = fields.Many2many('ir.attachment', 'res__var_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

    @api.model
    def create(self, vals):
        context = self.env.context
        print(self,'SELF = = = = =C\n',vals)
        result = super(ProductProduct, self.with_context(context)).create(vals)
        if vals.get('upload_product_var_image_ids'):
            for x in vals.get('upload_product_var_image_ids'):
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
                    # attachment_id = self.env['ir.attachment'].browse(x[1]).unlink()
                    # if attachment_id.datas:
                    #     attachment_id.unlink()

        return result

    def write(self, vals):
        context = self.env.context
        print(self,'SELF = = = = =W\n',vals)
        result = super(ProductProduct, self.with_context(context)).write(vals)
        if vals.get('upload_product_var_image_ids'):
            for x in vals.get('upload_product_var_image_ids'):
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
                    # attachment_id = self.env['ir.attachment'].browse(x[1])
                    # if attachment_id.datas:
                    #     attachment_id.unlink()

        return result

    def action_delete_all_tiktok_var_img(self):
        for dels in self:
            if dels.tiktok_product_var_image_ids:
                print(dels,'DELSS=var=')
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

# class IrAttachment(models.Model):
#     _inherit = "ir.attachment"

#     @api.model
#     def create(self, vals):
#         return super(IrAttachment, self).create(vals)