# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models

from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools.misc import groupby

from .delivery_request_objects import DeliveryCommodity, DeliveryPackage


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # -------------------------------- #
    # Internals for shipping providers #
    # -------------------------------- #

    invoice_policy = fields.Selection(
        selection_add=[('real', 'Real cost')],
        ondelete={'real': 'set default'},
        help="Estimated Cost: the customer will be invoiced the estimated cost of the shipping.\n"
        "Real Cost: the customer will be invoiced the real cost of the shipping, the cost of the"
        "shipping will be updated on the SO after the delivery."
    )

    route_ids = fields.Many2many(
        'stock.route', 'stock_route_shipping', 'shipping_id', 'route_id', 'Routes',
        domain=[('shipping_selectable', '=', True)])

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

    def get_return_label(self, pickings, tracking_number=None, origin_date=None):
        self.ensure_one()
        if self.can_generate_return:
            res = getattr(self, '%s_get_return_label' % self.delivery_type)(
                pickings, tracking_number, origin_date
            )
            if self.get_return_label_from_portal:
                pickings.return_label_ids.generate_access_token()
            return res

    def get_return_label_prefix(self):
        return 'LabelReturn-%s' % self.delivery_type

    def _get_delivery_label_prefix(self):
        return 'LabelShipping-%s' % self.delivery_type

    def _get_delivery_doc_prefix(self):
        return 'ShippingDoc-%s' % self.delivery_type

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

    # -------------------------------- #
    # get default packages/commodities #
    # -------------------------------- #

    def _get_packages_from_order(self, order, default_package_type):
        packages = []

        total_cost = 0
        for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type):
            total_cost += self._product_price_to_company_currency(line.product_qty, line.product_id, order.company_id)

        total_weight = order._get_estimated_weight() + default_package_type.base_weight
        order_weight = self.env.context.get('order_weight', False)
        total_weight = order_weight or total_weight
        if total_weight == 0.0:
            weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()
            raise UserError(_("The package cannot be created because the total weight of the products in the picking is 0.0 %s", weight_uom_name))
        # If max weight == 0 => division by 0. If this happens, we want to have
        # more in the max weight than in the total weight, so that it only
        # creates ONE package with everything.
        max_weight = default_package_type.max_weight or total_weight + 1
        total_full_packages = int(total_weight / max_weight)
        last_package_weight = total_weight % max_weight

        package_weights = [max_weight] * total_full_packages + ([last_package_weight] if last_package_weight else [])
        partial_cost = total_cost / len(package_weights)  # separate the cost uniformly
        order_commodities = self._get_commodities_from_order(order)

        # Split the commodities value uniformly as well
        for commodity in order_commodities:
            commodity.monetary_value /= len(package_weights)
            commodity.qty = max(1, commodity.qty // len(package_weights))

        for weight in package_weights:
            packages.append(DeliveryPackage(
                order_commodities,
                weight,
                default_package_type,
                total_cost=partial_cost,
                currency=order.company_id.currency_id,
                order=order,
            ))
        return packages

    def _get_packages_from_picking(self, picking, default_package_type):
        packages = []

        if picking.is_return_picking:
            commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
            weight = picking._get_estimated_weight() + default_package_type.base_weight
            packages.append(DeliveryPackage(
                commodities,
                weight,
                default_package_type,
                currency=picking.company_id.currency_id,
                picking=picking,
            ))
            return packages

        # Create all packages.
        for package in picking.package_ids:
            move_lines = picking.move_line_ids.filtered(lambda ml: ml.result_package_id == package)
            commodities = self._get_commodities_from_stock_move_lines(move_lines)
            package_total_cost = 0.0
            for quant in package.quant_ids:
                package_total_cost += self._product_price_to_company_currency(
                    quant.quantity, quant.product_id, picking.company_id
                )
            packages.append(DeliveryPackage(
                commodities,
                package.shipping_weight or package.weight,
                package.package_type_id,
                name=package.name,
                total_cost=package_total_cost,
                currency=picking.company_id.currency_id,
                picking=picking,
            ))

        # Create one package: either everything is in pack or nothing is.
        if picking.weight_bulk:
            commodities = self._get_commodities_from_stock_move_lines(picking.move_line_ids)
            package_total_cost = 0.0
            for move_line in picking.move_line_ids:
                package_total_cost += self._product_price_to_company_currency(
                    move_line.quantity, move_line.product_id, picking.company_id
                )
            packages.append(DeliveryPackage(
                commodities,
                picking.weight_bulk,
                default_package_type,
                name='Bulk Content',
                total_cost=package_total_cost,
                currency=picking.company_id.currency_id,
                picking=picking,
            ))
        elif not packages:
            raise UserError(_(
                "The package cannot be created because the total weight of the "
                "products in the picking is 0.0 %s",
                picking.weight_uom_name
            ))
        return packages

    def _get_commodities_from_order(self, order):
        commodities = []

        for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type and line.product_id.type in ['product', 'consu']):
            unit_quantity = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = line.product_id.country_of_origin.code or order.warehouse_id.partner_id.country_id.code
            commodities.append(DeliveryCommodity(
                line.product_id,
                amount=rounded_qty,
                monetary_value=line.price_reduce_taxinc,
                country_of_origin=country_of_origin,
            ))

        return commodities

    def _get_commodities_from_stock_move_lines(self, move_lines):
        commodities = []

        product_lines = move_lines.filtered(lambda line: line.product_id.type in ['product', 'consu'])
        for product, lines in groupby(product_lines, lambda x: x.product_id):
            unit_quantity = sum(
                line.product_uom_id._compute_quantity(
                    line.quantity,
                    product.uom_id)
                for line in lines)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = product.country_of_origin.code or lines[0].picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            unit_price = sum(line.sale_price for line in lines) / rounded_qty
            commodities.append(DeliveryCommodity(product, amount=rounded_qty, monetary_value=unit_price, country_of_origin=country_of_origin))

        return commodities

    def _product_price_to_company_currency(self, quantity, product, company):
        return company.currency_id._convert(quantity * product.standard_price, product.currency_id, company, fields.Date.today())

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
