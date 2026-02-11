# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosConfig(models.Model):
	_inherit = "pos.config"

	restrict_zero_qty = fields.Boolean(string='Restrict Zero Quantity')


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	pos_restrict_zero_qty = fields.Boolean(related="pos_config_id.restrict_zero_qty", readonly=False)


class ProductProductInherit(models.Model):
	_inherit = 'product.product'

	@api.model
	def _load_pos_data_fields(self, config_id):
		params = super()._load_pos_data_fields(config_id)
		params += ['qty_available', 'type']
		return params
