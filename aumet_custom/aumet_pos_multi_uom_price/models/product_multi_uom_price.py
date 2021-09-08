# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class multi_uom(models.Model):
    _name = 'product.multi.uom.price'
    _description = 'Product multiple uom price'

    product_id = fields.Many2one('product.template',
                                 _('Product'),
                                 required=True,
                                 readonly=True)
    category_id = fields.Many2one(related='product_id.uom_id.category_id')
    default_uom_id = fields.Many2one(related='product_id.uom_id')

    uom_id = fields.Many2one('uom.uom',
                             domain="[('category_id', '=', category_id),('id','!=',default_uom_id)]",
                             string=_("Unit of Measure"),
                             required=True)
    price = fields.Float(_('Price'),
                         required=True,
                         digits='Product Price')

    # EHdlF Convinación Producto-UOM debe ser única
    _sql_constraints = [
        ('product_multi_uom_price_uniq',
         'UNIQUE (product_id,uom_id)',
         _('Product-UOM must be unique and there are duplicates!'))]
