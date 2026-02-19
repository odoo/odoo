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


class ProductProduct(models.Model):
    """
    This is an Odoo model for product products. It inherits from the
    'product.product' model and extends its functionality by adding a
    computed field for product alert state.

     Methods:
        _compute_alert_tag(): Computes the value of the 'alert_tag' field based on the
        product's stock quantity and configured low stock alert parameters
    """
    _inherit = 'product.product'

    alert_tag = fields.Char(
        string='Product Alert Tag', compute='_compute_alert_tag',
        help='This field represents the alert tag of the product.')
    is_low_stock_alert = fields.Boolean(
        string="Low Stock Alert",
        help='This field determines the minimum stock quantity at which a low '
             'stock alert will be triggered.When the product quantity falls '
             'below this value, the background color for the product will be '
             'changed based on the alert state.',
        compute="_compute_is_low_stock_alert"
    )
    min_low_stock_alert = fields.Integer(
        string='Alert Quantity',
        help='Change the background color for the product based'
             'on the Alert Quant.')

    @api.depends('qty_available')
    def _compute_alert_tag(self):
        """Computes the value of the 'alert_tag' field based on the product's
        stock quantity and configured low stock alert parameters."""
        if self.env['ir.config_parameter'].sudo().get_param(
                'low_stocks_product_alert.is_low_stock_alert'):
            for rec in self:
                is_low_stock = rec.detailed_type == 'product' and rec.qty_available <= int(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'low_stocks_product_alert.min_low_stock_alert'))
                rec.alert_tag = rec.qty_available if is_low_stock else False
        elif self.env['ir.config_parameter'].sudo().get_param(
                'low_stocks_product_alert.is_low_stock_alert_individual'):
            for rec in self:
                is_low_stock_single = rec.detailed_type == 'product' and rec.qty_available <= int(
                    rec.min_low_stock_alert)
                rec.alert_tag = rec.qty_available if is_low_stock_single else False

    @api.depends_context('is_low_stock_alert_individual')
    def _compute_is_low_stock_alert(self):
        config_param = self.env['ir.config_parameter'].sudo()
        is_low_stock_alert_individual = config_param.get_param(
            'low_stocks_product_alert.is_low_stock_alert_individual')
        for product in self:
            product.is_low_stock_alert = bool(
                is_low_stock_alert_individual)
