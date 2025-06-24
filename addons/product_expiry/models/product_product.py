# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

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
        domain_quant = [('product_id', 'in', expiration_products.ids)] + expiration_products._get_domain_locations()[0]
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        domain_quant += [('removal_date', '<=', datetime.date.today())]
        Quant = self.env['stock.quant'].with_context(active_test=False)

        # A & B
        expired_unreserved_quants_res = {product.id: quantity - reserved_quantity for product, quantity, reserved_quantity in Quant._read_group(domain_quant, ['product_id'], ['quantity:sum', 'reserved_quantity:sum'])}

        # A & C
        wh = self.env['stock.warehouse'].search([])
        domain_quant[1] = ('location_id', 'in', wh.mapped('wh_qc_stock_loc_id').ids + wh.mapped('wh_input_stock_loc_id').ids)
        to_remove_in_transit = {product.id: quantity for product, quantity in Quant._read_group(domain_quant, ['product_id'], ['reserved_quantity:sum'])}

        for product in expiration_products:
            # A&B
            to_subtract = expired_unreserved_quants_res.get(product.id, 0.0)
            res[product.id]['free_qty'] = product.uom_id.round(res[product.id]['free_qty'])

            # A&B | A&C
            to_subtract += to_remove_in_transit.get(product.id, 0.0)
            res[product.id]['virtual_available'] = product.uom_id.round(res[product.id]['virtual_available'] - to_subtract)
        return res

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
