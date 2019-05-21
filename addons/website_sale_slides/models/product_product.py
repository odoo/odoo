from odoo import models, fields, api

class Product(models.Model):
    _inherit = "product.product"

    channel_id = fields.Many2one('slide.channel', 'Course', compute="_compute_channel_id", search='_search_channel_id')
    is_course = fields.Boolean('Is a course', compute="_compute_is_course", store=True)

    def _compute_channel_id(self):
        for product in self:
            channel = self.env['slide.channel'].search([['product_id','=',product.id]])
            product.channel_id = channel.id

    @api.depends('channel_id.product_id')
    def _compute_is_course(self):
        for product in self:
            if product.channel_id:
                product.is_course = True

    def _search_channel_id(self, operator, value):
        return [(1,'=',1)]