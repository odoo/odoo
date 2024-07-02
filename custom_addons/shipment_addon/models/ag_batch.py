from odoo import models, fields

class AgBatch(models.Model):
    _name = 'ag.batch'
    _description = 'Batch'

    parent_id = fields.Char(string='Parent ID')
    article_id = fields.Many2one('product.product', string='Article ID')