# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
import re

from odoo import api, fields, models, registry, SUPERUSER_ID, _
from odoo.tools.float_utils import float_round
from odoo.tools.misc import groupby
from odoo.exceptions import UserError

from .delivery_request_objects import DeliveryCommodity, DeliveryPackage


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _description = "Shipping Methods"
    _order = 'sequence, id'

    ''' A Shipping Provider

    In order to add your own external provider, follow these steps:

    1. Create your model MyProvider that _inherit 'delivery.carrier'
    2. Extend the selection of the field "delivery_type" with a pair
       ('<my_provider>', 'My Provider')
    3. Add your methods:
       <my_provider>_rate_shipment
       <my_provider>_send_shipping
       <my_provider>_get_tracking_link
       <my_provider>_cancel_shipment
       _<my_provider>_get_default_custom_package_code
       (they are documented hereunder)
    '''

    # -------------------------------- #
    # Internals for shipping providers #
    # -------------------------------- #

    name = fields.Char('Delivery Method', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(help="Determine the display order", default=10)
    # This field will be overwritten by internal shipping providers by adding their own type (ex: 'fedex')
    delivery_type = fields.Selection([('fixed', 'Fixed Price')], string='Provider', default='fixed', required=True)
    integration_level = fields.Selection([('rate', 'Get Rate'), ('rate_and_ship', 'Get Rate and Create Shipment')], string="Integration Level", default='rate_and_ship', help="Action while validating Delivery Orders")
    prod_environment = fields.Boolean("Environment", help="Set to True if your credentials are certified for production.")
    debug_logging = fields.Boolean('Debug logging', help="Log requests in order to ease debugging")
    company_id = fields.Many2one('res.company', string='Company', related='product_id.company_id', store=True, readonly=False)
    product_id = fields.Many2one('product.product', string='Delivery Product', required=True, ondelete='restrict')

    invoice_policy = fields.Selection([
        ('estimated', 'Estimated cost'),
        ('real', 'Real cost')
    ], string='Invoicing Policy', default='estimated', required=True,
    help="Estimated Cost: the customer will be invoiced the estimated cost of the shipping.\nReal Cost: the customer will be invoiced the real cost of the shipping, the cost of the shipping will be updated on the SO after the delivery.")

    country_ids = fields.Many2many('res.country', 'delivery_carrier_country_rel', 'carrier_id', 'country_id', 'Countries')
    state_ids = fields.Many2many('res.country.state', 'delivery_carrier_state_rel', 'carrier_id', 'state_id', 'States')
    zip_prefix_ids = fields.Many2many(
        'delivery.zip.prefix', 'delivery_zip_prefix_rel', 'carrier_id', 'zip_prefix_id', 'Zip Prefixes',
        help="Prefixes of zip codes that this carrier applies to. Note that regular expressions can be used to support countries with varying zip code lengths, i.e. '$' can be added to end of prefix to match the exact zip (e.g. '100$' will only match '100' and not '1000')")
    carrier_description = fields.Text(
        'Carrier Description', translate=True,
        help="A description of the delivery method that you want to communicate to your customers on the Sales Order and sales confirmation email."
             "E.g. instructions for customers to follow.")

    margin = fields.Float(help='This percentage will be added to the shipping price.')
    free_over = fields.Boolean('Free if order amount is above', help="If the order total amount (shipping excluded) is above or equal to this value, the customer benefits from a free shipping", default=False)
    amount = fields.Float(string='Amount', help="Amount of the order to benefit from a free shipping, expressed in the company currency")

    can_generate_return = fields.Boolean(compute="_compute_can_generate_return")
    return_label_on_delivery = fields.Boolean(string="Generate Return Label", help="The return label is automatically generated at the delivery.")
    get_return_label_from_portal = fields.Boolean(string="Return Label Accessible from Customer Portal", help="The return label can be downloaded by the customer from the customer portal.")

    supports_shipping_insurance = fields.Boolean(compute="_compute_supports_shipping_insurance")
    shipping_insurance = fields.Integer(
        "Insurance Percentage",
        help="Shipping insurance is a service which may reimburse senders whose parcels are lost, stolen, and/or damaged in transit.",
        default=0
    )

    _sql_constraints = [
        ('margin_not_under_100_percent', 'CHECK (margin >= -100)', 'Margin cannot be lower than -100%'),
        ('shipping_insurance_is_percentage', 'CHECK(shipping_insurance >= 0 AND shipping_insurance <= 100)', "The shipping insurance must be a percentage between 0 and 100."),
    ]

    @api.depends('delivery_type')
    def _compute_can_generate_return(self):
        for carrier in self:
            carrier.can_generate_return = False

    @api.depends('delivery_type')
    def _compute_supports_shipping_insurance(self):
        for carrier in self:
            carrier.supports_shipping_insurance = False

    def toggle_prod_environment(self):
        for c in self:
            c.prod_environment = not c.prod_environment

    def toggle_debug(self):
        for c in self:
            c.debug_logging = not c.debug_logging

    def install_more_provider(self):
        exclude_apps = ['delivery_barcode', 'delivery_stock_picking_batch', 'delivery_iot']
        return {
            'name': _('New Providers'),
            'view_mode': 'kanban,form',
            'res_model': 'ir.module.module',
            'domain': [['name', '=like', 'delivery_%'], ['name', 'not in', exclude_apps]],
            'type': 'ir.actions.act_window',
            'help': _('''<p class="o_view_nocontent">
                    Buy Odoo Enterprise now to get more providers.
                </p>'''),
        }

    def _is_available_for_order(self, order):
        self.ensure_one()
        order.ensure_one()
        if not self._match_address(order.partner_shipping_id):
            return False

        if self.delivery_type == 'base_on_rule':
            return self.rate_shipment(order).get('success')

        return True

    def available_carriers(self, partner):
        return self.filtered(lambda c: c._match_address(partner))

    def _match_address(self, partner):
        self.ensure_one()
        if self.country_ids and partner.country_id not in self.country_ids:
            return False
        if self.state_ids and partner.state_id not in self.state_ids:
            return False
        if self.zip_prefix_ids:
            regex = re.compile('|'.join(['^' + zip_prefix for zip_prefix in self.zip_prefix_ids.mapped('name')]))
            if not partner.zip or not re.match(regex, partner.zip.upper()):
                return False
        return True

    @api.onchange('integration_level')
    def _onchange_integration_level(self):
        if self.integration_level == 'rate':
            self.invoice_policy = 'estimated'

    @api.onchange('can_generate_return')
    def _onchange_can_generate_return(self):
        if not self.can_generate_return:
            self.return_label_on_delivery = False

    @api.onchange('return_label_on_delivery')
    def _onchange_return_label_on_delivery(self):
        if not self.return_label_on_delivery:
            self.get_return_label_from_portal = False

    @api.onchange('state_ids')
    def onchange_states(self):
        self.country_ids = [(6, 0, self.country_ids.ids + self.state_ids.mapped('country_id.id'))]

    @api.onchange('country_ids')
    def onchange_countries(self):
        self.state_ids = [(6, 0, self.state_ids.filtered(lambda state: state.id in self.country_ids.mapped('state_ids').ids).ids)]

    def _get_delivery_type(self):
        """Return the delivery type.

        This method needs to be overridden by a delivery carrier module if the delivery type is not
        stored on the field `delivery_type`.
        """
        self.ensure_one()
        return self.delivery_type

    # -------------------------- #
    # API for external providers #
    # -------------------------- #

    def rate_shipment(self, order):
        ''' Compute the price of the order shipment

        :param order: record of sale.order
        :return dict: {'success': boolean,
                       'price': a float,
                       'error_message': a string containing an error message,
                       'warning_message': a string containing a warning message}
                       # TODO maybe the currency code?
        '''
        self.ensure_one()
        if hasattr(self, '%s_rate_shipment' % self.delivery_type):
            res = getattr(self, '%s_rate_shipment' % self.delivery_type)(order)
            # apply fiscal position
            company = self.company_id or order.company_id or self.env.company
            res['price'] = self.product_id._get_tax_included_unit_price(
                company,
                company.currency_id,
                order.date_order,
                'sale',
                fiscal_position=order.fiscal_position_id,
                product_price_unit=res['price'],
                product_currency=company.currency_id
            )
            # apply margin on computed price
            res['price'] = float(res['price']) * (1.0 + (self.margin / 100.0))
            # save the real price in case a free_over rule overide it to 0
            res['carrier_price'] = res['price']
            # free when order is large enough
            amount_without_delivery = order._compute_amount_total_without_delivery()
            if res['success'] and self.free_over and self._compute_currency(order, amount_without_delivery, 'pricelist_to_company') >= self.amount:
                res['warning_message'] = _('The shipping is free since the order amount exceeds %.2f.') % (self.amount)
                res['price'] = 0.0
            return res

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
            res = getattr(self, '%s_get_return_label' % self.delivery_type)(pickings, tracking_number, origin_date)
            if self.get_return_label_from_portal:
                pickings.return_label_ids.generate_access_token()
            return res

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

    def log_xml(self, xml_string, func):
        self.ensure_one()

        if self.debug_logging:
            self.env.flush_all()
            db_name = self._cr.dbname

            # Use a new cursor to avoid rollback that could be caused by an upper method
            try:
                db_registry = registry(db_name)
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    IrLogging = env['ir.logging']
                    IrLogging.sudo().create({'name': 'delivery.carrier',
                              'type': 'server',
                              'dbname': db_name,
                              'level': 'DEBUG',
                              'message': xml_string,
                              'path': self.delivery_type,
                              'func': func,
                              'line': 1})
            except psycopg2.Error:
                pass

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

    fixed_price = fields.Float(compute='_compute_fixed_price', inverse='_set_product_fixed_price', store=True, string='Fixed Price')

    @api.depends('product_id.list_price', 'product_id.product_tmpl_id.list_price')
    def _compute_fixed_price(self):
        for carrier in self:
            carrier.fixed_price = carrier.product_id.list_price

    def _set_product_fixed_price(self):
        for carrier in self:
            carrier.product_id.list_price = carrier.fixed_price

    def fixed_rate_shipment(self, order):
        carrier = self._match_address(order.partner_shipping_id)
        if not carrier:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: this delivery method is not available for this address.'),
                    'warning_message': False}
        price = order.pricelist_id._get_product_price(self.product_id, 1.0)
        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False}

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

    # -------------------------------- #
    # get default packages/commodities #
    # -------------------------------- #

    def _get_packages_from_order(self, order, default_package_type):
        packages = []

        total_cost = 0
        for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type):
            total_cost += self._product_price_to_company_currency(line.product_qty, line.product_id, order.company_id)

        total_weight = order._get_estimated_weight() + default_package_type.base_weight
        if total_weight == 0.0:
            weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()
            raise UserError(_("The package cannot be created because the total weight of the products in the picking is 0.0 %s") % (weight_uom_name))
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
            packages.append(DeliveryPackage(order_commodities, weight, default_package_type, total_cost=partial_cost, currency=order.company_id.currency_id, order=order))
        return packages

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

    def _get_commodities_from_order(self, order):
        commodities = []

        for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type and line.product_id.type in ['product', 'consu']):
            unit_quantity = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = line.product_id.country_of_origin.code or order.warehouse_id.partner_id.country_id.code
            commodities.append(DeliveryCommodity(line.product_id, amount=rounded_qty, monetary_value=line.price_reduce_taxinc, country_of_origin=country_of_origin))

        return commodities

    def _get_commodities_from_stock_move_lines(self, move_lines):
        commodities = []

        product_lines = move_lines.filtered(lambda line: line.product_id.type in ['product', 'consu'])
        for product, lines in groupby(product_lines, lambda x: x.product_id):
            unit_quantity = sum(
                line.product_uom_id._compute_quantity(
                    line.qty_done if line.state == 'done' else line.reserved_uom_qty,
                    product.uom_id)
                for line in lines)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = product.country_of_origin.code or lines[0].picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            unit_price = sum(line.sale_price for line in lines) / rounded_qty
            commodities.append(DeliveryCommodity(product, amount=rounded_qty, monetary_value=unit_price, country_of_origin=country_of_origin))

        return commodities

    def _product_price_to_company_currency(self, quantity, product, company):
        return company.currency_id._convert(quantity * product.standard_price, product.currency_id, company, fields.Date.today())
