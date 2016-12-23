# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class ProductStyleShapes(models.Model):
	_name = 'product.style_shapes'
	name = fields.Char("Name of Shape", default="12 Point Burst")
	css = fields.Char("Name of Style", default="burst-12")

class ProductStyles(models.Model):
	_inherit = 'product.style'
	msg = fields.Char("Promotion Message", help="This is the promotional message that will appear on the ribbon or badge", default="Sale")
	text_color = fields.Char("Text Color", help="Color of the promotional text, Only HTML color codes are accepted", default= "FFFFFF", size=6)
	bg_color = fields.Char("Ribbon/Badge Color", help="Color of the ribbon or badge, Only HTML color codes are accepted", default="BB0000", size=6)
        shape = fields.Many2one('product.style_shapes', "Shape/Object", 
	              help="Choose of of the available objects to use")
	width = fields.Selection([(size,size ) for size in range (5,501)], string='Width (pixels)', default=40, 
		help="Width of the shape/Object in pixels")
	height = fields.Selection([(size,size ) for size in range (5,501)], string='Height (pixels)', default=40,
		help="Height of the shape/Object in pixels")
        top = fields.Selection([(size,size ) for size in range (0,101)],string='Position from Top (%)', default=40,
		help="Position of the shape/object from top of the product image")
        text_top = fields.Selection([(size,size ) for size in range (0,501)],default=9, string='Text Position from top (pixels)',
		help="Position of the promotional text from top")
	left = fields.Selection([(size,size ) for size in range (0,101)], default=40, string='Position from Left (%)',
		help="Position of the shape/object from left of the product image")
        font_size = fields.Selection([(size,size ) for size in range (0,101)], default=10, string='Font Size (pixels)', help="Font Size of the Promotional text")
        font_weight = fields.Selection([(size,size ) for size in range (100,1000, 100)],default=400, string='Font Weight',
		help="Font weight of the Promotional text, 400 is equivalent to 'normal' and 700 is equivalent to 'bold'")
