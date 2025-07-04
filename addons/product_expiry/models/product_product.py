# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from collections import defaultdict

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    free_qty = fields.Float(help="Available quantity (computed as Quantity On Hand "
             "- reserved quantity - quantity to remove)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")

    virtual_available = fields.Float(help="Forecast quantity (computed as Quantity On Hand "
             "- Outgoing + Incoming - Quantity to Remove)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        """
            For products that are perishable, we need to apply a correction to the free and the forecast quantity.
            The following rule defines when a quantity is no longer counted towards forecast quantity:
                It has a removal date of today or earlier (A) AND (
                    It is not reserved (B) OR
                    It is reserved but only because it is in transit (C, 2/3 step receipt in warehouse)
                )
            In short: quants to subtract = A & (B | C)
            In this method we calculate A&B and A&C separately (for expiration enabled products only) and then subtract
            the sum from the forecasted quantity.
            For the free quantity, we only need A&B, as the reserved quantity in transit is never 'free'.
        """
        res = super()._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)
        expiration_products = self.filtered(lambda p: p.use_expiration_date)
        if not expiration_products:
            return res
        domain_quant, domain_in, domain_out = ([('product_id', 'in', expiration_products.ids)] + domain for domain in expiration_products.with_context(move_lines=True)._get_domain_locations())
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_in += [('restrict_partner_id', '=', owner_id)]
            domain_out += [('restrict_partner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        domain_quant += [('removal_date', '<=', datetime.date.today())]
        Quant = self.env['stock.quant'].with_context(active_test=False)

        moves_in_res_past, moves_out_res_past = defaultdict(float), defaultdict(float)
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            # In case some stock came in or left while it was expired, we need to make sure we compensate for this.
            domain_in = [('state', '=', 'done'), ('date', '>', to_date), ('removal_date', '<=', datetime.date.today())] + domain_in
            domain_out = [('state', '=', 'done'), ('date', '>', to_date), ('removal_date', '<=', datetime.date.today())] + domain_out
            Move = self.env['stock.move.line'].with_context(active_test=False)
            groupby = ['product_id', 'product_uom_id']

            for product, uom, quantity in Move._read_group(domain_in, groupby, ['quantity:sum']):
                moves_in_res_past[product.id] += uom._compute_quantity(quantity, product.uom_id)

            for product, uom, quantity in Move._read_group(domain_out, groupby, ['quantity:sum']):
                moves_out_res_past[product.id] += uom._compute_quantity(quantity, product.uom_id)

        # A & B
        expired_unreserved_quants_res = {product.id: quantity - reserved_quantity for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}

        # A & C
        wh = self.env['stock.warehouse'].search([])
        domain_quant[1] = ('location_id', 'in', wh.mapped('wh_qc_stock_loc_id').ids + wh.mapped('wh_input_stock_loc_id').ids)
        to_remove_in_transit = {product.id: quantity for product, quantity in Quant._read_group(domain_quant, ['product_id'], ['reserved_quantity:sum'])}

        for product in expiration_products:
            # A&B
            to_subtract = expired_unreserved_quants_res.get(product.id, 0.0) - moves_in_res_past.get(product.id, 0.0) + moves_out_res_past.get(product, 0.0)
            res[product.id]['free_qty'] = product.uom_id.round(res[product.id]['free_qty'])

            # A&B | A&C
            to_subtract += to_remove_in_transit.get(product.id, 0.0)
            res[product.id]['virtual_available'] = product.uom_id.round(res[product.id]['virtual_available'] - to_subtract)
        return res

    def _get_domain_locations_new(self, location_ids):
        """
            As we cannot add a related field location_final_id on stock_move_line in stable, we use this hack to adapt
            the domain manually in case we need to work with stock move lines instead of stock moves.
            TODO: add a related field on stock_move_line instead and remove this override (as well as the move_lines context)
        """
        quants, in_moves, out_moves = super()._get_domain_locations_new(location_ids)
        if self.env.context.get('move_lines'):
            for domain in in_moves, out_moves:
                for idx, element in enumerate(domain):
                    if len(element) == 3 and element[0] == 'location_final_id':
                        domain[idx] = 'move_id.location_final_id', element[1], element[2]
        return quants, in_moves, out_moves


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    use_expiration_date = fields.Boolean(string='Use Expiration Date',
        help='When this box is ticked, you have the possibility to specify dates to manage'
        ' product expiration, on the product and on the corresponding lot/serial numbers')
    expiration_time = fields.Integer(string='Expiration Date',
        help='Number of days after the receipt of the products (from the vendor'
        ' or in stock after production) after which the goods may become dangerous'
        ' and must not be consumed. It will be computed on the lot/serial number.')
    use_time = fields.Integer(string='Best Before Date',
        help='Number of days before the Expiration Date after which the goods starts'
        ' deteriorating, without being dangerous yet. It will be computed on the lot/serial number.')
    removal_time = fields.Integer(string='Removal Date',
        help='Number of days before the Expiration Date after which the goods'
        ' should be removed from the stock and not be counted in the Fresh On Hand Stock anymore.'
        'It will be computed on the lot/serial number.')
    alert_time = fields.Integer(string='Alert Date',
        help='Number of days before the Expiration Date after which an alert should be'
        ' raised on the lot/serial number. It will be computed on the lot/serial number.')
