# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models

from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
from odoo.tools.safe_eval import safe_eval

from odoo.addons.delivery.models.delivery_request_objects import DeliveryCommodity, DeliveryPackage


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # -------------------------------- #
    # Internals for shipping providers #
    # -------------------------------- #

    delivery_type = fields.Selection(
        selection_add=[('base_on_rule', 'Based on Rules')],
        ondelete={
            'base_on_rule': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0}),
        },
    )
    invoice_policy = fields.Selection(
        selection_add=[('real', 'Real cost')],
        ondelete={'real': 'set default'},
        help="Estimated Cost: the customer will be invoiced the estimated cost of the shipping.\n"
             "Real Cost: the customer will be invoiced the real cost of the shipping, the cost of "
             "the shipping will be updated on the SO after the delivery."
    )

    # -------------------------- #
    # API for external providers #
    # -------------------------- #

    def send_shipping(self, pickings):
        ''' Send the package to the service provider

        :param pickings: A recordset of pickings
        :return list: A list of dictionaries (one per picking) containing of the form::
                         { 'exact_price': price,
                           'tracking_number': number }
                           # TODO missing labels per package
                           # TODO missing currency
                           # TODO missing success, error, warnings
        '''
        self.ensure_one()
        if hasattr(self, '%s_send_shipping' % self.delivery_type):
            return getattr(self, '%s_send_shipping' % self.delivery_type)(pickings)

    def get_return_label(self,pickings, tracking_number=None, origin_date=None):
        self.ensure_one()
        if self.can_generate_return:
            return getattr(self, '%s_get_return_label' % self.delivery_type)(pickings, tracking_number, origin_date)

    def get_return_label_prefix(self):
        return 'ReturnLabel-%s' % self.delivery_type

    def get_tracking_link(self, picking):
        ''' Ask the tracking link to the service provider

        :param picking: record of stock.picking
        :return str: an URL containing the tracking link or False
        '''
        self.ensure_one()
        if hasattr(self, '%s_get_tracking_link' % self.delivery_type):
            return getattr(self, '%s_get_tracking_link' % self.delivery_type)(picking)

    def cancel_shipment(self, pickings):
        ''' Cancel a shipment

        :param pickings: A recordset of pickings
        '''
        self.ensure_one()
        if hasattr(self, '%s_cancel_shipment' % self.delivery_type):
            return getattr(self, '%s_cancel_shipment' % self.delivery_type)(pickings)

    def _get_default_custom_package_code(self):
        """ Some delivery carriers require a prefix to be sent in order to use custom
        packages (ie not official ones). This optional method will return it as a string.
        """
        self.ensure_one()
        if hasattr(self, '_%s_get_default_custom_package_code' % self.delivery_type):
            return getattr(self, '_%s_get_default_custom_package_code' % self.delivery_type)()
        else:
            return False

    # ------------------------------------------------ #
    # Fixed price shipping, aka a very simple provider #
    # ------------------------------------------------ #

    def fixed_send_shipping(self, pickings):
        res = []
        for p in pickings:
            res = res + [{'exact_price': p.carrier_id.fixed_price,
                          'tracking_number': False}]
        return res

    def fixed_get_tracking_link(self, picking):
        return False

    def fixed_cancel_shipment(self, pickings):
        raise NotImplementedError()

    # ----------------------------------- #
    # Based on rule delivery type methods #
    # ----------------------------------- #

    def base_on_rule_rate_shipment(self, order):
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: this delivery method is not available for this address.'),
                    'warning_message': False}

        try:
            price_unit = self._get_price_available(order)
        except UserError as e:
            return {'success': False,
                    'price': 0.0,
                    'error_message': e.args[0],
                    'warning_message': False}

        price_unit = self._compute_currency(order, price_unit, 'company_to_pricelist')

        return {'success': True,
                'price': price_unit,
                'error_message': False,
                'warning_message': False}

    def _get_price_available(self, order):
        total = super()._get_price_available(order)
        weight = volume = quantity = 0
        for line in order.order_line:
            if line.state == 'cancel':
                continue
            if not line.product_id or line.is_delivery:
                continue
            if line.product_id.type == "service":
                continue
            qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            quantity += qty
        # weight is either,
        # 1- weight chosen by user in choose.delivery.carrier wizard passed by context
        # 2- saved weight to use on sale order
        # 3- total order line weight as fallback
        weight = self.env.context.get('order_weight') or order.shipping_weight or weight
        return self._get_price_from_picking(total, weight=weight, volume=volume, quantity=quantity)

    def _get_price_dict(self, total, weight=0, volume=0, quantity=0):
        '''Override of `delivery` to extend the dictionary of pricing factors.'''
        return {
            **super()._get_price_dict(total, weight=weight, volume=volume, quantity=quantity),
            'volume': volume,
            'weight': weight,
            'wv': volume * weight,
            'quantity': quantity
        }

    def _get_price_from_picking(self, total, weight=0, volume=0, quantity=0):
        super()._get_price_from_picking(total, weight=weight, volume=volume, quantity=quantity)
        price_dict = self._get_price_dict(total, weight=weight, volume=volume, quantity=quantity)
        if self.free_over and total >= self.amount:
            return 0
        for line in self.price_rule_ids:
            if safe_eval(line.variable + line.operator + str(line.max_value), price_dict):
                return line.list_base_price + line.list_price * price_dict[line.variable_factor]

    def base_on_rule_send_shipping(self, pickings):
        res = []
        for p in pickings:
            carrier = self._match_address(p.partner_id)
            if not carrier:
                raise ValidationError(_('There is no matching delivery rule.'))
            res = res + [{'exact_price': p.carrier_id._get_price_available(p.sale_id) if p.sale_id else 0.0,  # TODO cleanme
                          'tracking_number': False}]
        return res

    def base_on_rule_get_tracking_link(self, picking):
        return False

    def base_on_rule_cancel_shipment(self, pickings):
        raise NotImplementedError()

    # -------------------------------- #
    # get default packages/commodities #
    # -------------------------------- #

    def _get_packages_from_picking(self, picking, default_package_type):
        packages = []

        if picking.is_return_picking:
            commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
            weight = picking._get_estimated_weight() + default_package_type.base_weight
            packages.append(DeliveryPackage(commodities, weight, default_package_type, currency=picking.company_id.currency_id, picking=picking))
            return packages

        # Create all packages.
        for package in picking.package_ids:
            move_lines = picking.move_line_ids.filtered(lambda ml: ml.result_package_id == package)
            commodities = self._get_commodities_from_stock_move_lines(move_lines)
            package_total_cost = 0.0
            for quant in package.quant_ids:
                package_total_cost += self._product_price_to_company_currency(quant.quantity, quant.product_id, picking.company_id)
            packages.append(DeliveryPackage(commodities, package.shipping_weight or package.weight, package.package_type_id, name=package.name, total_cost=package_total_cost, currency=picking.company_id.currency_id, picking=picking))

        # Create one package: either everything is in pack or nothing is.
        if picking.weight_bulk:
            commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
            package_total_cost = 0.0
            for move_line in picking.move_line_ids:
                package_total_cost += self._product_price_to_company_currency(move_line.qty_done, move_line.product_id, picking.company_id)
            packages.append(DeliveryPackage(commodities, picking.weight_bulk, default_package_type, name='Bulk Content', total_cost=package_total_cost, currency=picking.company_id.currency_id, picking=picking))
        elif not packages:
            raise UserError(_("The package cannot be created because the total weight of the products in the picking is 0.0 %s") % (picking.weight_uom_name))

        return packages

    def _get_commodities_from_stock_move_lines(self, move_lines):
        commodities = []

        for line in move_lines.filtered(lambda line: line.product_id.type in ['product', 'consu']):
            if line.state == 'done':
                unit_quantity = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)
            else:
                unit_quantity = line.product_uom_id._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = line.product_id.country_of_origin.code or line.picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            commodities.append(DeliveryCommodity(line.product_id, amount=rounded_qty, monetary_value=line.sale_price, country_of_origin=country_of_origin))

        return commodities
