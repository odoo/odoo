# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Shonima (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import models
from odoo.tools.float_utils import float_compare, float_round


class StockMove(models.Model):
    """Inherited StockMove class to super the functions"""
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """ super the function o update the lot/serial number in
        stock.move.line"""
        self.ensure_one()
        vals = {
            'move_id': self.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'company_id': self.company_id.id,
        }
        auto_generate = self.env['ir.config_parameter'].sudo().get_param(
            'auto_generate_lot_number.is_auto_generate')
        if auto_generate:
            serial_number_type = self.env[
                'ir.config_parameter'].sudo().get_param(
                'auto_generate_lot_number.serial_number_type')
            if serial_number_type == 'global':
                vals.update({
                    'lot_name': self.env['ir.sequence'].next_by_code('res'
                                                                     '.config'
                                                                     '.settings'),
                })
            else:
                vals.update({
                    'lot_name': self.product_id.product_tmpl_id._number_next_actual(),
                })
        if quantity:
            rounding = self.env['decimal.precision'].precision_get('Product '
                                                                   'Unit of '
                                                                   'Measure')
            uom_quantity = self.product_id.uom_id._compute_quantity(quantity,
                                                                    self.product_uom,
                                                                    rounding_method='HALF-UP')
            uom_quantity = float_round(uom_quantity, precision_digits=rounding)
            uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(
                uom_quantity, self.product_id.uom_id,
                rounding_method='HALF-UP')
            if float_compare(quantity, uom_quantity_back_to_product_uom,
                             precision_digits=rounding) == 0:
                vals = dict(vals, reserved_uom_qty=uom_quantity)
            else:
                vals = dict(vals, reserved_uom_qty=quantity,
                            product_uom_id=self.product_id.uom_id.id)
        if reserved_quant:
            package = reserved_quant.package_id
            vals = dict(
                vals,
                location_id=reserved_quant.location_id.id,
                lot_id=reserved_quant.lot_id.id or False,
                package_id=package.id or False,
                owner_id=reserved_quant.owner_id.id or False,
            )
        return vals

    def action_show_details(self):
        """This used to overriden 'view_stock_move_operations' view by
        'view_stock_move_nosuggest_operations_custom' view"""
        res = super(StockMove, self).action_show_details()
        auto_generate = self.env['ir.config_parameter'].sudo().get_param(
            'auto_generate_lot_number.is_auto_generate')
        if auto_generate:
            view = self.env.ref('auto_generate_lot_number'
                                '.view_stock_move_nosuggest_operations_custom')
            res.update({
                'views': [(view.id, 'form')],
                'view_id': view.id,
            })
        return res
