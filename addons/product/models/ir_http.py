# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models
from odoo.http import request
from odoo.tools.float_utils import float_get_decimals

_logger = logging.getLogger(__name__)


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()
        result.update(self.get_uom_data())
        return result

    def get_uom_data(self):
        """ Fetches the company's configured UoMs for display and returns their characteristics
        """
        weight_uom = request.env['product.uom'].browse(int(request.env['ir.config_parameter'].sudo().get_param('database_weight_uom_id')))
        if not weight_uom:
            _logger.warning("No unit of measure found to display weights, please make sure to set one in the General Settings. Falling back to hard-coded Kilos.")
            weight_data = {'symbol': 'kg', 'factor': 1, 'digits': [69, 3]}
        else:
            weight_data = {'symbol': weight_uom.name, 'factor': weight_uom.factor, 'position': 'after', 'digits': [69, float_get_decimals(weight_uom.rounding)]}

        volume_uom = request.env['product.uom'].browse(int(request.env['ir.config_parameter'].sudo().get_param('database_volume_uom_id')))
        if not volume_uom:
            _logger.warning("No unit of measure found to display volumes, please make sure to set one in the General Settings. Falling back to hard-coded Liters.")
            volume_data = {'symbol': 'Liter(s)', 'factor': 1, 'digits': [69, 3]}
        else:
            volume_data = {'symbol': volume_uom.name, 'factor': volume_uom.factor, 'position': 'after', 'digits': [69, float_get_decimals(volume_uom.rounding)]}

        return {
            'weight_uom': weight_data,
            'volume_uom': volume_data,
        }
