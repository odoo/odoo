# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import math
import requests
from werkzeug.urls import url_join


from odoo import fields, _
from odoo.exceptions import UserError
from odoo.tools import float_repr, float_compare

# More information at : https://api.sendcloud.dev/docs/sendcloud-public-api/integrations
BASE_URL = "https://panel.sendcloud.sc/api/v2/"
MULTICOLLO_MAX_PACKAGE = 20

class SendCloud:

    def __init__(self, public_key, private_key, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.auth = (public_key, private_key)

    def _get_shipping_functionalities(self):
        return self._send_request('shipping-functionalities')

    def _get_shipping_products(self, from_country, is_return=False, carrier=None, weight=None, to_country=None, sizes=None, size_unit='centimeter'):
        params = {'from_country': from_country, 'returns': is_return}
        if carrier:
            params.update({'carrier': carrier})
        if to_country:
            params.update({'to_country': to_country})
        if weight:
            params.update({'weight': weight, 'weight_unit': 'gram'})
        if sizes:
            params.update({
                'length': sizes.get('length', 0),
                'height': sizes.get('height', 0),
                'width': sizes.get('width', 0),
                'length_unit': size_unit,
                'height_unit': size_unit,
                'width_unit': size_unit,
            })
        return self._send_request('shipping-products', params=params)

    def _get_shipping_rate(self, carrier, order=None, picking=None, parcel=None, order_weight=None):
        # Get source, destination and weight
        if order:
            to_country = order.partner_shipping_id.country_id.code
            from_country = order.warehouse_id.partner_id.country_id.code
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines:
                raise UserError(_("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s", ", ".join(error_lines.product_id.mapped('name'))))
            packages = carrier._get_packages_from_order(order, carrier.sendcloud_default_package_type_id)
            total_weight = order_weight if order_weight else sum(pack.weight for pack in packages)
        elif picking:
            to_country = picking.destination_country_code
            from_country = picking.location_id.warehouse_id.partner_id.country_id.code
            total_weight = float(parcel['weight'])
        else:
            raise UserError(_('No picking or order provided'))
        if not to_country or not from_country:
            raise UserError(_('Make sure country codes are set in partner country and warehouse country'))
        total_weight = int(carrier.sendcloud_convert_weight(total_weight, grams=True))
        if total_weight < carrier.sendcloud_shipping_id.min_weight and order:
            raise UserError(_('Order below minimum weight of carrier'))
        if parcel:
            shipping_methods = [{
                'id': parcel.get('shipment', {}).get('id'),
                'weight': int(float(parcel.get('weight', 0))*1000),  # parcel weight is defined in kg
            }]
        else:
            shipping_methods = self._get_shipping_methods(carrier, from_country, to_country, total_weight=total_weight)

        if not shipping_methods or (len(shipping_methods) == 1 and not shipping_methods[0]):
            raise UserError(_('There is no shipping method available for this order with the selected carrier'))

        packages_no = 1
        if order:
            default_package = carrier.sendcloud_default_package_type_id
            target_weight = default_package.max_weight if default_package else False
            packages_no, total_weight = self._split_shipping(carrier.sendcloud_shipping_id, total_weight, target_weight)
        if packages_no > 1:
            # We're forcefully calling this method from a sale order, as we only want an estimation of the rating, take the 'heaviest' methods
            shipping_methods = [m for m in shipping_methods if m['properties']['max_weight'] == carrier.sendcloud_shipping_id.max_weight]  # We're sure here there's at least one matching method as max_weight was updated in _get_shipping_methods
        shipping_prices = self._get_shipping_prices(shipping_methods, to_country, from_country, total_weight)

        if not shipping_prices:
            raise UserError(_('There is no rate available for this order with the selected shipping product'))

        shipping_price = min(shipping_prices.items(), key=lambda p: float(p[1]['price']))
        price = float(shipping_price[1].get('price')) * packages_no
        currency = shipping_price[1].get('currency')
        currency_id = carrier.env['res.currency'].with_context(active_test=False).search([('name', '=', currency)])
        if not currency_id:
            raise UserError(_('Could not find currency %s', currency))

        to_currency_id = order.currency_id if order else picking.sale_id.currency_id
        converted_price = currency_id._convert(price, to_currency_id, carrier.env.company, fields.Date.context_today(carrier))
        return converted_price, packages_no

    def _send_shipment(self, picking, is_return=False):
        sender_id = None
        if not is_return:
            # get warehouse for each picking and get the sender address to use for shipment
            sender_id = self._get_pick_sender_address(picking)
        parcels = self._prepare_parcel(picking, sender_id, is_return)

        # the id of the access_point needs to be passed as parameter following Sendcloud API's
        if 'access_point_address' in picking.sale_id and picking.sale_id.access_point_address:
            for parcel in parcels:
                parcel['to_service_point'] = picking.sale_id.access_point_address['id']

        data = {
            'parcels': parcels
        }
        parameters = {
            'errors': 'verbose-carrier',
        }
        res = self._send_request('parcels', 'post', data, params=parameters)
        res_parcels = res.get('parcels')
        if not res_parcels:
            error_message = res['failed_parcels'][0].get('errors', False)
            raise UserError(_("Something went wrong, parcel not returned from Sendcloud:\n %s'.", error_message))
        return res_parcels

    def _track_shipment(self, parcel_id):
        parcel = self._send_request(f'parcels/{parcel_id}')
        return parcel['parcel']

    def _cancel_shipment(self, parcel_id):
        res = self._send_request(f'parcels/{parcel_id}/cancel', method='post')
        return res

    def _get_document(self, url):
        ''' Returns pdf content of document to print '''
        self.logger(f'get {url}', 'sendcloud get document')
        try:
            res = self.session.request(method='get', url=url, timeout=60)
        except Exception as err:
            self.logger(str(err), f'sendcloud response {url}')
            raise UserError(_('Something went wrong, please try again later!!'))

        self.logger(f'{res.content}', 'sendcloud get document response')
        if res.status_code != 200:
            raise UserError(_('Could not get document!'))
        return res.content

    def _get_addresses(self):
        res = self._send_request('user/addresses/sender')
        return res.get('sender_addresses', [])

    def _split_shipping(self, shipping_product_id, total_weight, target_weight=False):
        # if the weight is greater than max weight and source is order (initial estimate)
        # split the weight into packages instead of returning no price / offer
        shipping_count = 1
        shipping_weight = total_weight
        # max weight from sendcloud is 1 gram extra (eg. if max allowed weight = 3000g, sendcloud_shipping_id.max_weight = 3001g)
        max_weight = target_weight if target_weight else shipping_product_id.max_weight - 1
        if target_weight or total_weight > max_weight:
            shipping_count = math.ceil(total_weight / max_weight)
            shipping_weight = max_weight
        return shipping_count, shipping_weight

    def _get_shipping_prices(self, shipping_methods, to_country, from_country, weight=None):
        shipping_prices = dict()
        params = {
            'shipping_method_id': None,
            'to_country': to_country,
            'from_country': from_country,
            'weight': weight,
            'weight_unit': 'gram',
        }

        for shipping_method in shipping_methods:
            shipping_id = params['shipping_method_id'] = shipping_method['id']
            if not weight:
                params['weight'] = shipping_method['properties']['max_weight'] - 1  # the weight of a shipping_method is always in gram
            # the API response is an Array of 1 dict with price and currency (usually EUR)
            res = self._send_request('shipping-price', params=params)[0]
            if res.get('price'):
                shipping_prices[shipping_id] = res
            elif shipping_id == 8:  # Sendcloud Unstamped Letter
                # shipping id 8 is a test shipping and does not provide a price, but we still need the flow to continue
                # the check is done after the request since in the future if price is actually returned it will be passed correctly
                shipping_prices = {8: {'price': 0.0, 'currency': 'EUR'}}
        return shipping_prices

    def _get_shipping_methods(self, carrier_id, from_country, to_country, total_weight=None, is_return=False, sizes=None):
        """
        We're now working with a sendcloud's PRODUCT
        We must fetch the differents METHODS in that product, in order to find the most appropriate !
        We may however still be in the case where there isn't a single method able to handle the total weight of the order.
        In this last case, we may split the shipping in multiple packages as before.
        """
        sendcloud_product_id = carrier_id.sendcloud_return_id if is_return else carrier_id.sendcloud_shipping_id
        if not sendcloud_product_id:
            return None
        shipping_code = sendcloud_product_id.sendcloud_code
        shipping_carrier = sendcloud_product_id.carrier
        # Despite the fact that the sendcloud's documentation says the product
        #  weight range is inclusive, a search with total_weight == max_weight
        #  returns no result.
        single_shipping = total_weight and total_weight < sendcloud_product_id.max_weight
        if single_shipping:
            shipping_products = self._get_shipping_products(from_country, is_return=is_return, carrier=shipping_carrier, to_country=to_country, weight=total_weight, sizes=sizes)
        else:
            shipping_products = self._get_shipping_products(from_country, is_return=is_return, carrier=shipping_carrier, to_country=to_country, sizes=sizes)

        shipping_product = next(filter(lambda p: p['code'] == shipping_code, shipping_products), None)
        if not shipping_product:
            if single_shipping:
                # single_shipping may be false-positive due to the local value 'sendcloud_product_id.max_weight'
                # we call back this method without filtering the call by weight to reach the update of local cache
                return self._get_shipping_methods(carrier_id, from_country, to_country, is_return=is_return, sizes=sizes)
            else:
                return None

        if not single_shipping:
            # Update product local values
            max_allowed_weight = shipping_product['weight_range']['max_weight'] # This data is only valid if we didn't set the 'weight' arg in _get_shipping_products call
            self._validate_shipping_product_max_weight(sendcloud_product_id, max_allowed_weight)

        user_filters = None if is_return else carrier_id.sendcloud_product_functionalities
        shipping_ids = self._filtered_shipping_method_ids(shipping_product['methods'], user_filters)

        if not shipping_ids:
            raise UserError(_("There's no shipping method matching all your selected filters for this picking/order."))

        return list(filter(lambda m: m['id'] in shipping_ids, shipping_product['methods']))

    def _filtered_shipping_method_ids(self, shipping_methods, user_filters):
        """
        Apply user filters on methods
        for each filter key : [values]
            if the ONLY value for a key is None:
               then the key MUST NOT be present in the method functions
            if there are "other values" AND None:
               then OR :
                  the key IS present AND it's value IN filter's values
                  the key IS NOT present
            if there are ONLY "other values":
                  the key IS present AND it's value IN filter's values
        Default : return all the ids when there's no user_filters
        Return : set of id
        """
        shipping_ids = {m['id'] for m in shipping_methods}
        if not user_filters:
            return shipping_ids
        for func, options in user_filters.items():
            def pass_filter(shipping_method):
                return (func not in shipping_method['functionalities'] and 'None' in options) or (func in shipping_method['functionalities'] and shipping_method['functionalities'][func] in options)

            filtered_ids = {m['id'] for m in shipping_methods if pass_filter(m)}
            if not filtered_ids:
                return []
            elif not shipping_ids:
                shipping_ids = filtered_ids
            else:
                shipping_ids &= filtered_ids
        return shipping_ids

    def _send_request(self, endpoint, method='get', data=None, params=None, route=BASE_URL):

        url = url_join(route, endpoint)
        self.logger(f'{url}\n{method}\n{data}\n{params}', f'sendcloud request {endpoint}')
        if method not in ['get', 'post']:
            raise Exception(f'Unhandled request method {method}')
        try:
            res = self.session.request(method=method, url=url, json=data, params=params, timeout=60)
            self.logger(f'{res.status_code} {res.text}', f'sendcloud response {endpoint}')
            res = res.json()
        except Exception as err:
            self.logger(str(err), f'sendcloud response {endpoint}')
            raise UserError(_('Something went wrong, please try again later!!'))

        if 'error' in res:
            raise UserError(res['error']['message'])
        return res

    def _prepare_parcel_items(self, packages, carrier, products_values=None):
        if not isinstance(packages, list):
            packages = [packages]
        if not products_values:
            products_values = dict()
        parcel_items = {}
        for pkg in packages:
            for commodity in pkg.commodities:
                key = commodity.product_id.id
                if key in parcel_items:
                    parcel_items[key]['quantity'] += commodity.qty
                    continue

                if commodity.product_id.id in products_values:
                    value = products_values[commodity.product_id.id]['avg_value']
                else:
                    value = commodity.monetary_value

                hs_code = commodity.product_id.hs_code or ''
                for ch in [' ', '.']:
                    hs_code = hs_code.replace(ch, '')
                parcel_items[key] = {
                    'description': commodity.product_id.name,
                    'quantity': commodity.qty,
                    'weight': float_repr(carrier.sendcloud_convert_weight(commodity.product_id.weight), 3),
                    'value': round(value, 2),
                    'hs_code': hs_code[:8],
                    'origin_country': commodity.country_of_origin or '',
                    'sku': commodity.product_id.barcode or '',
                }
        return list(parcel_items.values())

    def _get_house_number(self, address):
        house_number = re.findall(r"([1-9]+\w*)", address)
        if house_number:
            return house_number[0]
        return ' '

    def _validate_partner_details(self, partner):
        if not partner.phone and not partner.mobile:
            raise UserError(_('%(partner_name)s phone required', partner_name=partner.name))
        if not partner.email:
            raise UserError(_('%(partner_name)s email required', partner_name=partner.name))
        if not all([partner.street, partner.city, partner.zip, partner.country_id]):
            raise UserError(_('The %s address needs to have the street, city, zip, and country', partner.name))
        if (partner.street and len(partner.street) > 75) or (partner.street2 and len(partner.street2) > 75):
            raise UserError(_('Each address line can only contain a maximum of 75 characters. You can split the address into multiple lines to try to avoid this limitation.'))

    def _validate_shipping_product_max_weight(self, shipping_product_id, fresh_max_weight):
        if shipping_product_id.max_weight != fresh_max_weight:
            shipping_product_id.max_weight = fresh_max_weight
            return False
        return True

    def _get_max_package_sizes(self, package_ids):
        """
            Return the largest size for each dimension of a list of package

            :param delivery.carrier self: the Sendcloud delivery carrier
            :param list[DeliveryPackage] package_ids: A list of package
            :return: A dict of size for each dimension or None if all sizes are 0
            :rtype: dict[str, int] or None
        """
        sizes = {
                "length": 0,
                "height": 0,
                "width": 0,
        }
        for pkg in package_ids:
            for axis in ("length", "height", "width"):
                sizes[axis] = max(sizes[axis], pkg.dimension.get(axis))
        return sizes

    def _prepare_parcel(self, picking, sender_id, is_return):
        # Pre-checks
        carrier_id = picking.carrier_id
        delivery_packages = carrier_id._get_packages_from_picking(picking, carrier_id.sendcloud_default_package_type_id) # If nothing to return -> Error
        if any(not pkg.weight for pkg in delivery_packages):
            raise UserError(_("Ensure picking has shipping weight, if using packages, each package should have a shipping weight"))
        #Prepare API call and process data
        to_partner_id = picking.partner_id
        from_partner_id = picking.picking_type_id.warehouse_id.partner_id
        if is_return:
            to_partner_id, from_partner_id = from_partner_id, to_partner_id
        from_country, to_country = from_partner_id.country_id.code, to_partner_id.country_id.code
        self._validate_partner_details(to_partner_id)
        shipping_weight = int(carrier_id.sendcloud_convert_weight(picking.shipping_weight, grams=True))
        to_europe = to_partner_id.country_id.code in to_partner_id.env.ref('base.europe').country_ids.mapped('code')
        use_multicollo = carrier_id.sendcloud_use_batch_shipping and to_europe
        single_shipping = len(delivery_packages) == 1 or (use_multicollo and len(delivery_packages) <= 20)
        api_weight = shipping_weight if single_shipping else None

        # Fetch shipping methods compatible with current picking
        shipping_methods = self._get_shipping_methods(picking.carrier_id, from_country, to_country, api_weight, is_return)
        sendcloud_product_id = carrier_id.sendcloud_return_id if is_return else carrier_id.sendcloud_shipping_id
        user_uom_max_weight = carrier_id.sendcloud_convert_weight(sendcloud_product_id.max_weight - 1, grams=True, reverse=True)  # grams to user uom
        user_weight_uom = carrier_id.env['product.template'].sudo()._get_weight_uom_id_from_ir_config_parameter()
        if not shipping_methods:
            raise UserError(_('There is no shipping method available for this picking with the selected carrier'))
        elif any(float_compare(pkg.weight, user_uom_max_weight, precision_rounding=user_weight_uom.rounding) > 0 for pkg in delivery_packages):
            overweight_products = picking.move_ids.filtered(lambda m: float_compare(m.product_id.weight, user_uom_max_weight, precision_rounding=m.product_uom.rounding) > 0)
            not_packed = bool(not picking.package_ids and picking.weight_bulk)
            if not_packed:
                message = _('The total weight of your transfer is too heavy for the heaviest available shipping method.')
            else:
                message = _('Some packages in your transfer are too heavy for the heaviest available shipping method.')
            message += _("\nTry to distribute your products across your packages so that they weigh less than %(max_weight)s %(unit)s or choose another carrier.", max_weight=user_uom_max_weight, unit=user_weight_uom.name)
            if overweight_products:
                product_moves = ", ".join(overweight_products.mapped('name'))
                message += _("""\nAdditionally, some individual product(s) are too heavy for the heaviest available shipping method.
                             \nDivide the quantity of the following product(s) across your packages if possible or choose another carrier:\n\t%s""", product_moves)
            raise UserError(message)

        shipping_prices = self._get_shipping_prices(shipping_methods, to_country, from_country)
        # Assign consequent price to each method, delete the method if no price is available
        for shipping_method in reversed(shipping_methods):
            price = shipping_prices.get(shipping_method['id'], {}).get('price')
            if not price:
                shipping_methods.remove(shipping_method)  # Safe thanks to reversed()
            else:
                shipping_method['price'] = price

        method_shipments = self._assign_packages_to_methods(carrier_id, delivery_packages, shipping_methods, use_multicollo)
        parcel_common = self._prepare_parcel_common_data(picking, is_return, sender_id)
        products_values = self._get_products_values(picking.sale_id)

        total_value = 0.0
        if picking.sale_id:
            total_value = sum(line.price_reduce_taxinc * line.product_uom_qty for line in
                picking.sale_id.order_line.filtered(
                    lambda l: l.product_id.type in ('consu', 'product') and not l.display_type
                )
            )
        else:
            total_value = sum([line.product_id.lst_price * line.product_qty for line in picking.move_ids])
        total_value = float_repr(total_value, 2)

        parcels = []
        for shipping in method_shipments:  # shipping = { 'id': (int), 'packages': [pkg or [pkg]]}, each id is unique among the whole list
            parcel_common['shipment'] = {
                'id': shipping['id'],
            }
            for pkg in shipping['packages']:  # pkg is either a single pkg or a list of pkg
                parcel = dict(parcel_common)
                if isinstance(pkg, list):
                    max_sizes = self._get_max_package_sizes(pkg)
                    parcel.update({
                        'weight': float_repr(sum(p.weight for p in pkg), 3),
                        'length': max_sizes['length'],
                        'width': max_sizes['width'],
                        'height': max_sizes['height'],
                        'quantity': len(pkg),
                    })
                else:
                    parcel.update({
                        'weight': float_repr(pkg.weight, 3),
                        'length': pkg.dimension['length'],
                        'width': pkg.dimension['width'],
                        'height': pkg.dimension['height'],
                    })

                parcel['parcel_items'] = self._prepare_parcel_items(pkg, carrier_id, products_values)
                parcel['total_order_value'] = total_value
                parcels.append(parcel)

        return parcels

    def _assign_packages_to_methods(self, carrier_id, delivery_packages, shipping_methods, use_multicollo=False):
        sorted_methods = self._get_cheapest_method_by_weight_ranges(shipping_methods)
        # Now methods are sorted by price :
        #   For regular shippings, we can fit packages in the first matching method
        #   For multicollo :
        #       Group packages wisely to minimize the cost if there's more than 20 of them
        #       Fitting of method is done by batch of packages
        failed_assignation = []
        for package in delivery_packages:
            sendcloud_uom_package_weight = int(carrier_id.sendcloud_convert_weight(package.weight, grams=True))  # user uom to grams
            cheapest_method = next((m for m in sorted_methods if m['weight']['min'] <= sendcloud_uom_package_weight <= m['weight']['max']), None)
            if cheapest_method:
                cheapest_method['packages'].append(package)
            else:
                failed_assignation.append(package)

        if failed_assignation:
            details = "\n\t- ".join(f"{pkg.name}: {pkg.weight}" for pkg in failed_assignation)
            raise UserError(_("There's no method with matching weight range for packages :\n%s\nYou can either choose another carrier, change your filters or redefine the content of your package(s).") % details)

        sorted_methods = [m for m in sorted_methods if m['packages']]  # Remove methods without package
        if not use_multicollo:
            return sorted_methods

        multicollo_batch = [{
            'id': False,
            'packages': [[]],
        }]
        pkg_number = math.ceil(len(delivery_packages)/MULTICOLLO_MAX_PACKAGE)
        min_batch_size = len(delivery_packages)%MULTICOLLO_MAX_PACKAGE
        max_batch_size = MULTICOLLO_MAX_PACKAGE
        for method in reversed(sorted_methods):
            while True:  # the current method may be set for more than 20pkg, ensure to assign all of them
                batch_size = len(multicollo_batch[-1]['packages'][-1])
                method_pkg_size = len(method['packages'])
                if not multicollo_batch[-1]['id']:
                    multicollo_batch[-1]['id'] = method['id']

                if (batch_size + method_pkg_size) <= max_batch_size:
                    multicollo_batch[-1]['packages'][-1].extend(method['packages'])
                    break  # Exit the 'infinite' loop, as the else condition always minimize batch_size and method_pkg_size that are defined on basis of finite sets, we will forcefully reach this point
                else:
                    to_fulfill = max_batch_size - batch_size
                    multicollo_batch[-1]['packages'][-1].extend(method['packages'][:to_fulfill-1])
                    method['packages'] = method['packages'][to_fulfill:]
                    pkg_number -= 1
                    max_batch_size = MULTICOLLO_MAX_PACKAGE
                    multicollo_batch[-1]['packages'].append([])

            if min_batch_size <= len(multicollo_batch[-1]['packages'][-1]):  # As we're iterating in reverse order (on price), we want to ship a min. of package in early batches to minimize the cost
                pkg_number -= 1
                if pkg_number == 0:
                    break
                min_batch_size = (min_batch_size - len(multicollo_batch[-1]['packages'][-1])) % 20
                max_batch_size = MULTICOLLO_MAX_PACKAGE
                multicollo_batch.append({
                    'id': False,
                    'packages': [[]],
                })
            else:
                max_batch_size = min_batch_size  # Apply minimum append strategy on next iteration
        return multicollo_batch

    def _get_products_values(self, sale_order=None):
        """
        If the parcel come from a sale order, we take the price from it.
        However, as we may have the same product sold at different prices in the same SO,
        and as sendcloud is strict (particularly when it comes to customs), we define the average price per product
        """
        products_values = dict()
        if not sale_order:
            return products_values

        for line in sale_order.order_line:
            if line.product_id.type not in ('consu', 'product') or line.display_type:
                continue
            if line.product_id.id in products_values:
                products_values[line.product_id.id]['tot_qty'] += line.product_uom_qty
                products_values[line.product_id.id]['tot_value'] += line.price_reduce_taxinc * line.product_uom_qty
            else:
                products_values[line.product_id.id] = {
                    'tot_qty': line.product_uom_qty,
                    'tot_value': line.price_reduce_taxinc * line.product_uom_qty,
                }
        for val in products_values.values():
            val.update({
                'avg_value': float(val['tot_value'])/float(val['tot_qty'])
            })
        return products_values

    def _get_cheapest_method_by_weight_ranges(self, shipping_methods):
        # order methods by min_weight(1st) and max_weight(2nd) and price(3rd)
        shipping_methods = sorted(shipping_methods, key=lambda m: (m['properties']['min_weight'], m['properties']['max_weight'], m['price']))
        sorted_methods = []
        # Define best method by weight range
        for method in shipping_methods:
            if sorted_methods and method['properties']['min_weight'] == sorted_methods[-1]['weight']['min'] and method['properties']['max_weight'] == sorted_methods[-1]['weight']['max']:
                continue  # Due to previous sort, price of current method is forcefully greater for the same weight range (which is worse)
            sorted_methods.append({
                'id': method['id'],
                'price': method['price'],
                'weight': {
                    'min': method['properties']['min_weight'],
                    'max': method['properties']['max_weight'],
                },
                'packages': [],
            })

        sorted_methods = sorted(sorted_methods, key=lambda m: m['price'])
        return sorted_methods

    def _prepare_parcel_common_data(self, picking, is_return, sender_id=False):
        if 'access_point_address' in picking.sale_id and picking.sale_id.access_point_address:
            to_partner_id = picking.partner_id.parent_id
        else:
            to_partner_id = picking.partner_id
        from_partner_id = picking.picking_type_id.warehouse_id.partner_id
        if is_return:
            to_partner_id, from_partner_id = from_partner_id, to_partner_id
        carrier_id = picking.carrier_id
        apply_rules = carrier_id.sendcloud_shipping_rules
        sendcloud_product_id = carrier_id.sendcloud_return_id if is_return else carrier_id.sendcloud_shipping_id

        if picking.sale_id:
            currency_name = picking.sale_id.currency_id.name
        else:
            currency_name = picking.company_id.currency_id.name

        parcel_common = {
            'name': to_partner_id.name[:75],
            'company_name': to_partner_id.commercial_company_name[:50] if to_partner_id.commercial_company_name else '',
            'address': to_partner_id.street,
            'address_2': to_partner_id.street2 or '',
            'house_number': self._get_house_number(to_partner_id.street),
            'city': to_partner_id.city or '',
            'country_state': to_partner_id.state_id.code or '',
            'postal_code': to_partner_id.zip,
            'country': to_partner_id.country_id.code,
            'telephone': to_partner_id.phone or to_partner_id.mobile or '',
            'email': to_partner_id.email or '',
            'request_label': True,
            'apply_shipping_rules': apply_rules,
            'is_return': is_return,
            'shipping_method_checkout_name': sendcloud_product_id.name,
            'order_number': picking.sale_id.name or picking.name,
            'customs_shipment_type': 4 if is_return else 2,
            'customs_invoice_nr': picking.origin or '',
            'total_order_value_currency': currency_name
        }
        if sender_id:
            # "sender_id" implies that "not is_return" (c.f. send_shipment())
            # So we're sure here that sender_id and from_partner_id holds the warehouse's address
            parcel_common.update({
                'sender_address': sender_id
            })
        elif from_partner_id:
            # As we can't use 'sender_address' and 'from_*' fields at the same time in the API call
            # we only use from_partner_id in case sender_id is false
            self._validate_partner_details(from_partner_id)
            parcel_common.update({
                'from_name': from_partner_id.name[:75],
                'from_company_name': from_partner_id.commercial_company_name[:50] if from_partner_id.commercial_company_name else '',
                'from_house_number': self._get_house_number(from_partner_id.street),
                'from_address_1': from_partner_id.street or '',
                'from_address_2': from_partner_id.street2 or '',
                'from_city': from_partner_id.city or '',
                'from_state': from_partner_id.state_id.code or '',
                'from_postal_code': from_partner_id.zip or '',
                'from_country': from_partner_id.country_id.code,
                'from_telephone': from_partner_id.phone or from_partner_id.mobile or '',
                'from_email': from_partner_id.email or '',
            })
        return parcel_common

    def _get_pick_sender_address(self, picking):
        warehouse_name = picking.location_id.warehouse_id.name.lower().replace(' ', '')
        addresses = self._get_addresses()
        res_id = None
        for addr in addresses:
            label = addr.get('label', '').lower().replace(' ', '')
            contact_name = addr.get('contact_name', '').lower().replace(' ', '')
            if warehouse_name in (label, contact_name):
                res_id = addr['id']
                break
        if not res_id:
            raise UserError(_('No address found with contact name %s on your sendcloud account.', picking.location_id.warehouse_id.name))
        return res_id
