# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CustomModel(models.Model):
    """
    A sample custom model for the Cistech module
    """
    _name = 'cistech.custom.model'
    _description = 'Cistech Custom Model'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    
    # Example relations
    # partner_id = fields.Many2one('res.partner', string='Partner')
    # product_ids = fields.Many2many('product.product', string='Products')
    
    # Example computed field
    # @api.depends('field1', 'field2')
    # def _compute_field(self):
    #     for record in self:
    #         record.computed_field = record.field1 + record.field2
    # computed_field = fields.Float(string='Computed Field', compute='_compute_field') 