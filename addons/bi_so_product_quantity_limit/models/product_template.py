# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
	_inherit = "product.template"

	min_qty = fields.Float(string= "Minimum Qty")
	max_qty = fields.Float(string= "Maximum Qty")

	@api.constrains('min_qty','max_qty')
	def qty_validate(self):
		if self.min_qty > self.max_qty:
			raise ValidationError("Maximum Qty Should be Greater than Minimum Qty")