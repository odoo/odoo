from odoo import models, fields

class AgAllocation(models.Model):
    _name = 'ag.allocation'
    _description = 'Allocation'

    # TODO: should be fk to shipment table
    shipment_id = fields.Char(string='Shipment ID')
    
    supplier_id = fields.Many2one('res.partner', string='Supplier ID')
    customer_id = fields.Many2one('res.partner', string='Customer ID')
    
    article_id = fields.Many2one('product.product', string='Article ID')
    quantity = fields.Float(string="Quantity")

    batch_id = fields.Many2one('ag.batch', string='Batch ID')