# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Anfas Faisal K (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class ResConfig(models.TransientModel):
    """
    This is an Odoo model for configuration settings. It inherits from the
    'res.config.settings' model and extends its functionality by adding
    fields for low stock alert configuration

    """
    _inherit = 'res.config.settings'

    is_low_stock_alert = fields.Boolean(
        string="Low Stock Alert For All Products",
        help='This field determines the minimum stock quantity at which a low '
             'stock alert will be triggered.When the product quantity falls '
             'below this value, the background color for the product will be '
             'changed based on the alert state.',
        config_parameter='low_stocks_product_alert.is_low_stock_alert')
    is_low_stock_alert_individual = fields.Boolean(
        string="Low Stock Alert For Individual Product",
        help='This field determines the minimum stock quantity at which a low '
             'stock alert will be triggered.When the product quantity falls '
             'below this value, the background color for the product will be '
             'changed based on the alert state.',
        config_parameter='low_stocks_product_alert.is_low_stock_alert_individual',
        default=False)
    min_low_stock_alert = fields.Integer(
        string='Alert Quantity', default=0,
        help='Change the background color for the product based'
             'on the Alert Quant.',
        config_parameter='low_stocks_product_alert.min_low_stock_alert')

    @api.onchange('is_low_stock_alert_individual')
    def _onchange_is_low_stock_alert_individual(self):
        """The function is used to change the stock alert in the product form"""
        if self.env['ir.config_parameter'].sudo().get_param(
                'low_stocks_product_alert.is_low_stock_alert_individual'):
            product_variants = self.env['product.product'].search([])
            for rec in product_variants:
                rec.is_low_stock_alert = True
