import logging
import uuid

from odoo import http, Command
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.json import scriptsafe as json
from odoo.addons.pos_urban_piper import const
from .data_validator import object_of, list_of

from werkzeug import exceptions

_logger = logging.getLogger(__name__)

order_data_schema = object_of({
    'order': object_of({
        'items': list_of(object_of({
            'title': True,
            'price': True,
            'merchant_id': True,
            'quantity': True,
        })),
        'details': object_of({
            'order_subtotal': True,
            'total_taxes': True,
            'order_state': True,
            'channel': True,
            'id': True,
        }),
        'payment': True,
        'store': object_of({
            'merchant_ref_id': True,
        }),
    }),
    'customer': object_of({
        'name': True,
        'email': True,
        'phone': True,
        'address': True,
    }),
})

order_status_update_schema = object_of({
    'order_id': True,
    'new_state': True,
    'store_id': True,
})

rider_status_update_schema = object_of({
    'delivery_info': object_of({
        'current_state': True,
        'delivery_person_details': object_of({
            'name': True,
            'phone': True,
        }),
    }),
    'order_id': True,
    'store': object_of({
        'ref_id': True,
    }),
})

store_action_schema = object_of({
    'status': True,
    'platform': True,
    'action': True,
    'location_ref_id': True,
})


class PosUrbanPiperController(http.Controller):

    @http.route('/urbanpiper/webhook/<string:event_type>', type='json', methods=['POST'], auth='public')
    def webhook(self, event_type):
        if not consteq(request.httprequest.headers.get('X-Urbanpiper-Uuid'), request.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.uuid')):
            # Ignore request if it's not from the same database
            return
        data = request.get_json_data()
        if event_type == 'order_placed':
            self._handle_data(data, order_data_schema, self._create_order, event_type)
        elif event_type == 'order_status_update':
            self._handle_data(data, order_status_update_schema, self._order_status_update, event_type)
        elif event_type == 'rider_status_update':
            self._handle_data(data, rider_status_update_schema, self._rider_status_update, event_type)
        elif event_type == 'store_action':
            self._handle_data(data, store_action_schema, self._store_action, event_type)

    def _handle_data(self, data, schema, handler, event_type):
        is_valid, error = schema(data)
        pos_config = request.env['pos.config']
        if is_valid:
            if event_type == 'order_placed':
                pos_config_sudo = request.env['pos.config'].sudo().search([
                    ('urbanpiper_store_identifier', '=', data['order']['store']['merchant_ref_id'])
                ])
                if not pos_config_sudo:
                    _logger.warning("UrbanPiper: Store not found for order %r", data['order'].get('id'))
                    pos_config.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_webhook_store_not_found')
                    return exceptions.BadRequest()
                if not pos_config_sudo.current_session_id:
                    _logger.warning("UrbanPiper: Session is not open for %r", pos_config_sudo.name)
                    pos_config.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_webhook_session_not_open%s')
                    return exceptions.BadRequest()
            handler(data)
        else:
            pos_config.log_xml("Payload - %s. Error - %s" % (data, error), 'urbanpiper_webhook_%s' % (event_type))
            _logger.warning("UrbanPiper: %r", error)

    def _prepare_price_unit_from_baseline(self, total_tax, price_unit, product, pos_config_sudo):
        base_line = total_tax._prepare_base_line_for_taxes_computation(
            request.env['pos.order.line'],
            currency_id=pos_config_sudo.company_id.currency_id,
            tax_ids=total_tax,
            price_unit=price_unit,
            quantity=1,
            special_mode="total_included",
            product_id=product
        )
        total_tax._add_tax_details_in_base_line(base_line, pos_config_sudo.company_id)
        total_tax._round_base_lines_tax_details([base_line], pos_config_sudo.company_id)
        tax_types = total_tax.flatten_taxes_hierarchy().mapped('price_include')
        if len(set(tax_types)) > 1:
            _logger.warning("UrbanPiper: Multiple tax types found for product %s. Using the first one.", product.name)
        price_unit = base_line['tax_details']['total_included'] if tax_types and tax_types[0] else base_line['tax_details']['total_excluded']
        return price_unit

    def _create_order(self, data):
        order = data['order']
        customer = data['customer']
        customer_address = customer['address']
        details = order['details']
        PosOrder = request.env['pos.order'].sudo()
        existing_order = PosOrder.search([
            ('delivery_identifier', '=', details['id']),
        ])
        if existing_order:
            _logger.info("UrbanPiper: Order %r already exists.", details['id'])
            return False
        pos_config_sudo = request.env['pos.config'].sudo().search([
            ('urbanpiper_store_identifier', '=', order['store']['merchant_ref_id'])
        ])
        # Check the customer exists with the same name and phone number
        customer_sudo = request.env['res.partner'].sudo().search(
            [('name', '=', customer['name']), '|', ('phone', '=', customer['phone']), ('mobile', '=', customer['phone'])]
        )
        if not customer_sudo:
            customer_sudo = request.env['res.partner'].sudo().create({
                'name': customer['name'],
                'phone': customer['phone'],
                'email': customer['email'],
                'mobile': customer['phone'],
                'street': customer_address.get('line_1'),
                'street2': customer_address.get('line_2'),
                'city': customer_address.get('city'),
                'zip': customer_address.get('pin'),
            })
        else:
            customer_sudo.write({
                'email': customer['email'],
                'street': customer_address.get('line_1'),
                'street2': customer_address.get('line_2'),
                'zip': customer_address.get('pin'),
                'city': customer_address.get('city'),
            })
        order_reference = PosOrder._generate_unique_reference(
            pos_config_sudo.current_session_id.id,
            pos_config_sudo.id,
            pos_config_sudo.current_session_id.sequence_number,
            order['details']['channel'].capitalize()
        )

        def get_prep_time(details):
            data = details.get('prep_time')
            if data:
                return data.get('estimated') or data.get('max')

        pos_delivery_provider = request.env['pos.delivery.provider'].sudo().search([('technical_name', '=', details['channel'])], limit=1)
        if not pos_delivery_provider:
            _logger.warning("UrbanPiper: Delivery provider not found for %r", details['channel'])
            pos_config_sudo.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_webhook_delivery_provider_not_found')
            return exceptions.BadRequest()

        lines = [self._create_order_line(line, pos_config_sudo) for line in order['items']]
        for charge in details.get('charges', []):
            charge_title = charge.get('title', '').lower()
            charge_product = request.env.ref('pos_urban_piper.product_other_charges', False)
            if 'delivery' in charge_title:
                charge_product = request.env.ref('pos_urban_piper.product_delivery_charges', False)
            elif 'packaging' in charge_title:
                charge_product = request.env.ref('pos_urban_piper.product_packaging_charges', False)
            if not charge_product:
                _logger.warning("UrbanPiper: Charge product not found for %r", charge_title)
                pos_config_sudo.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_charge_product_not_found')
                continue
            line_tax = request.env["account.tax"]
            domain = request.env['account.tax']._check_company_domain(pos_config_sudo.company_id)
            total_tax = charge_product.sudo().taxes_id.filtered_domain(domain)
            price_unit = charge.get('value')
            if charge.get("taxes", []):
                tax_ids = []
                charge_value = charge.get("value")
                for tax_payload in charge.get("taxes", []):
                    if not tax_payload.get("value"):
                        continue
                    tax_rate = int((100 * tax_payload["value"]) / charge_value)
                    tax_domain = self._get_tax_domain(pos_config_sudo, tax_rate)
                    tax_record = request.env["account.tax"].sudo().search(tax_domain, limit=1)
                    if tax_record:
                        tax_ids.append(tax_record.id)
                line_tax = request.env["account.tax"].browse(tax_ids)
            elif total_tax:
                price_unit = self._prepare_price_unit_from_baseline(total_tax, price_unit, charge_product, pos_config_sudo)
                line_tax = total_tax
            tax_ids_after_fiscal_position = pos_config_sudo.urbanpiper_fiscal_position_id.map_tax(line_tax)
            taxes = tax_ids_after_fiscal_position.compute_all(price_unit, pos_config_sudo.company_id.currency_id, 1, product=charge_product)
            lines.append(Command.create({
                'product_id': charge_product.sudo().id,
                'full_product_name': charge.get('title', charge_product.sudo().name),
                'qty': 1,
                'price_unit': price_unit,
                'tax_ids': [Command.set(line_tax.ids)],
                'price_subtotal': taxes['total_excluded'],
                'price_subtotal_incl': taxes['total_included'],
                'note': charge.get('title'),
                'uuid': str(uuid.uuid4())
            }))
        discounts = details.get('ext_platforms', [{}])[0].get('discounts', [])
        general_note = "\n".join([
            f"{pos_delivery_provider.name} Discount: {pos_config_sudo.company_id.currency_id.symbol} {discount.get('value')}"
            for discount in discounts if not discount.get('is_merchant_discount')
        ])
        for discount in discounts:
            if discount.get('is_merchant_discount'):
                discount_product = request.env['product.product'].sudo().search([
                    ('name', '=', 'Merchant Discount'),
                    ('default_code', '=', 'MRDT')
                ], limit=1)
                if not discount_product:
                    discount_product = request.env['product.product'].sudo().create({
                        'name': 'Merchant Discount',
                        'type': 'service',
                        'list_price': 0,
                        'available_in_pos': True,
                        'taxes_id': [(5, 0, 0)],
                        'default_code': 'MRDT'
                    })
                domain = request.env['account.tax']._check_company_domain(pos_config_sudo.company_id)
                line_tax = discount_product.sudo().taxes_id.filtered_domain(domain)
                if line_tax:
                    price_unit = self._prepare_price_unit_from_baseline(
                        line_tax, -discount.get('value'), discount_product, pos_config_sudo)
                else:
                    price_unit = -discount.get('value')
                tax_ids_after_fiscal_position = pos_config_sudo.urbanpiper_fiscal_position_id.map_tax(line_tax)
                taxes = tax_ids_after_fiscal_position.compute_all(
                    -price_unit, pos_config_sudo.company_id.currency_id, 1, product=discount_product)
                lines.append(Command.create({
                    'product_id': discount_product.sudo().id,
                    'qty': 1,
                    'price_unit': price_unit,
                    'tax_ids': [Command.set(line_tax.ids)],
                    'price_subtotal': taxes['total_excluded'],
                    'price_subtotal_incl': taxes['total_included'],
                    'note': discount.get('code'),
                    'uuid': str(uuid.uuid4()),
                }))
        number = str((pos_config_sudo.current_session_id.id % 10) * 100 + pos_config_sudo.current_session_id.sequence_number % 100).zfill(3)
        delivery_order = PosOrder.create({
            'name': order_reference,
            'partner_id': customer_sudo.id,
            'pos_reference': order_reference,
            'sequence_number': number,
            'tracking_number': number,
            'config_id': pos_config_sudo.id,
            'session_id': pos_config_sudo.current_session_id.id,
            'company_id': pos_config_sudo.company_id.id,
            'fiscal_position_id': pos_config_sudo.urbanpiper_fiscal_position_id.id,
            'lines': lines,
            'amount_paid': 0.0, #calculation is done below
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'delivery_identifier': details['id'],
            'delivery_status': details['order_state'].lower(),
            'general_note': "\n".join(
                x for x in [details.get('instructions'), general_note] if x and x.strip()
            ),
            'delivery_provider_id': pos_delivery_provider.id,
            'prep_time': get_prep_time(details),
            'delivery_json': json.dumps(data),
            'user_id':  pos_config_sudo.current_session_id.user_id.id,
            'uuid': str(uuid.uuid4()),
        })
        delivery_order._compute_prices()
        pos_config_sudo.current_session_id.sequence_number += 1
        self.after_delivery_order_create(delivery_order, details, pos_config_sudo)
        pos_config_sudo._send_delivery_order_count(delivery_order.id)

    def after_delivery_order_create(self, delivery_order, details, pos_config_sudo):
        pass

    def _get_tax_value(self, taxes_data, pos_config):
        """
        Override in delivery provider modules.
        """
        taxes = request.env['account.tax']
        for tax_line in taxes_data:
            taxes |= request.env['account.tax'].sudo().search([
                ('tax_group_id.name', '=', tax_line.get('title')),
                ('amount', '=', tax_line.get('rate'))
            ], limit=1)
        return taxes

    def _get_tax_domain(self, pos_config, tax_percentage):
        return [('company_id', '=', pos_config.company_id.id), ('amount', '=', tax_percentage)]

    def _create_order_line(self, line_data, pos_config_sudo):
        value_ids_lst = []
        note = ''
        if line_data.get('options_to_add'):
            note = '\n'.join([f"{option.get('title')} X {option.get('quantity')}" for option in line_data['options_to_add']])
            merchant_value_lst = [option.get('merchant_id') for option in line_data['options_to_add']]
            value_ids_lst = [int(vid.split('-')[1]) for vid in merchant_value_lst]
        price_extra = sum(option.get('total_price', 0) for option in line_data.get('options_to_add', []))
        attribute_value_ids = []
        values_to_remove = []
        if value_ids_lst:
            for value in value_ids_lst:
                value_id = request.env['product.attribute.value'].sudo().browse(value)
                if value_id.attribute_id.create_variant == 'no_variant' or value_id.attribute_id.display_type == 'multi':
                    product_option = request.env['product.template.attribute.value'].sudo().search([
                        ('product_tmpl_id', '=', int(line_data['merchant_id'].split('-')[0])),
                        ('product_attribute_value_id', '=', value)
                    ])
                    if product_option:
                        attribute_value_ids.append(product_option.id)
                    values_to_remove.append(value)
        variant_value_lst = [value for value in value_ids_lst if value not in values_to_remove]
        line_taxes = request.env['account.tax']
        main_product = self._product_template_to_product_variant(int(line_data['merchant_id'].split('-')[0]), variant_value_lst)
        price_unit = float(line_data['price'] + price_extra)
        tax_ids = main_product.taxes_id.filtered_domain(request.env['account.tax']._check_company_domain(pos_config_sudo.company_id))
        if line_data.get('taxes'):
            line_taxes = self._get_tax_value(line_data.get('taxes'), pos_config_sudo)
        elif tax_ids:
            price_unit = self._prepare_price_unit_from_baseline(tax_ids, price_unit, main_product, pos_config_sudo)
            line_taxes = tax_ids
        tax_ids_after_fiscal_position = pos_config_sudo.urbanpiper_fiscal_position_id.map_tax(line_taxes)
        taxes = tax_ids_after_fiscal_position.compute_all(price_unit, pos_config_sudo.company_id.currency_id, int(line_data['quantity']), product=main_product)
        lines = Command.create({
            'product_id': main_product.id,
            'full_product_name': line_data['title'],
            'qty': int(line_data['quantity']),
            'attribute_value_ids': attribute_value_ids,
            'price_extra': price_extra,
            'price_unit': price_unit,
            'price_subtotal': taxes['total_excluded'],
            'price_subtotal_incl': taxes['total_included'],
            'tax_ids': [Command.set(line_taxes.ids)] if line_taxes else None,
            'note': "\n".join(
                x for x in [line_data.get('instructions'), note] if x and x.strip()
            ),
            'uuid': str(uuid.uuid4()),
        })
        return lines

    def _product_template_to_product_variant(self, tmpl_id, value_ids):
        products = request.env['product.product'].sudo().search([('product_tmpl_id', '=', tmpl_id)])
        if products:
            if not value_ids:
                return products[0]
            if len(products) == 1:
                return products[0]
            product = products.filtered(
                lambda l: sorted(l.product_template_variant_value_ids.product_attribute_value_id.ids) == sorted(value_ids)
            )
            return product

    def _order_status_update(self, data):
        def _get_status_seq(status):
            return const.ORDER_STATUS_MAPPING[status][0]
        current_order_id = request.env['pos.order'].sudo().search([('delivery_identifier', '=', str(data['order_id']))])
        if not current_order_id:
            _logger.warning("UrbanPiper: Order %r not found for update the status.", data['order_id'])
            return
        if _get_status_seq(current_order_id.delivery_status.replace('_', ' ').title()) < _get_status_seq(data['new_state']):
            current_order_id.delivery_status = const.ORDER_STATUS_MAPPING[data['new_state']][1]
            pos_config_sudo = request.env['pos.config'].sudo().search([
                ('urbanpiper_store_identifier', '=', data['store_id'])
            ])
            if current_order_id.state == 'draft' and current_order_id.delivery_status in ('food_ready', 'dispatched', 'completed'):
                pos_config_sudo._make_order_payment(current_order_id)
            pos_config_sudo._send_delivery_order_count(current_order_id.id)

    def _rider_status_update(self, data):
        current_order_id = request.env['pos.order'].sudo().search([('delivery_identifier', '=', str(data['order_id']))])
        if not current_order_id:
            _logger.warning("UrbanPiper: Order %r not found for update the rider status.", data['order_id'])
            return
        current_order_id.delivery_rider_json = json.dumps(data['delivery_info'])
        pos_config_sudo = request.env['pos.config'].sudo().search([
            ('urbanpiper_store_identifier', '=', data['store']['ref_id'])
        ])
        pos_config_sudo._send_delivery_order_count()

    def _store_action(self, data):
        pos_config_sudo = request.env['pos.config'].sudo().search([
            ('urbanpiper_store_identifier', '=', data['location_ref_id'])
        ])
        pos_config_sudo._store_action_update(data)
