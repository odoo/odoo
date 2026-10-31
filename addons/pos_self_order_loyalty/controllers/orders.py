from odoo import fields, http
from odoo.http import request
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from odoo.tools.mail import email_normalize
from odoo.exceptions import UserError
from werkzeug.exceptions import Forbidden, Unauthorized
import re


class PosSelfOrderControllerLoyalty(PosSelfOrderController):
    def _get_partner_information(self, pos_config, partner):
        """Data of the customer the client just identified as, with its loyalty cards.

        The partner id is signed (see pos.order._get_signed_self_partner_id): it's what the
        client sends back as the order's partner, and what the server trusts.
        """
        empty = {'res.partner': [], 'loyalty.card': [], 'loyalty.rule': [], 'loyalty.reward': [], 'loyalty.program': []}
        if not partner:
            return empty
        today = fields.Date.context_today(pos_config)
        loyalty_programs = pos_config._get_program_ids().filtered(lambda p: p.program_type in ['loyalty', 'ewallet'])
        loyalty_cards = pos_config.env['loyalty.card'].search([
            ('program_id', 'in', loyalty_programs.ids),
            ('partner_id', '=', partner.id),
            '|', ('expiration_date', '=', False), ('expiration_date', '>=', today),
        ])
        reward_ids = loyalty_cards.program_id.reward_ids.filtered_domain(pos_config.env['loyalty.reward']._get_active_products_domain())
        partners = pos_config.env['res.partner']._load_pos_self_data_read(partner, pos_config)
        for partner_data in partners:
            partner_data['id'] = pos_config.env['pos.order']._get_signed_self_partner_id(pos_config, partner_data['id'])
        return {
            **empty,
            **self._add_product_linked_to_reward(reward_ids, pos_config),
            'res.partner': partners,
            'loyalty.card': self._read_self_order_cards(pos_config, loyalty_cards, partner),
            'loyalty.rule': pos_config.env['loyalty.rule']._load_pos_self_data_read(loyalty_cards.program_id.rule_ids, pos_config),
            'loyalty.reward': pos_config.env['loyalty.reward']._load_pos_self_data_read(reward_ids, pos_config),
            'loyalty.program': pos_config.env['loyalty.program']._load_pos_self_data_read(loyalty_cards.program_id, pos_config),
        }

    def _read_self_order_cards(self, pos_config, cards, partner):
        """Card data whose partner matches the client's identified `partner` (signed id).

        Only the identified partner's id is signed: signing another partner's would hand the
        client a proof of that customer's identity.
        """
        signed_partner_id = partner and pos_config.env['pos.order']._get_signed_self_partner_id(pos_config, partner.id)
        cards_data = pos_config.env['loyalty.card']._load_pos_self_data_read(cards, pos_config)
        for card_data in cards_data:
            card_data['partner_id'] = signed_partner_id if partner and card_data['partner_id'] == partner.id else False
        return cards_data

    @http.route('/pos-self-order/get-identified-partner', auth='public', type='jsonrpc', website=True)
    def get_identified_partner(self, access_token, partner_id):
        """The up-to-date data of the customer a client identified as earlier (signed id)."""
        pos_config = self._verify_pos_config(access_token)
        partner = pos_config.env['pos.order']._get_self_partner_from_token(pos_config, partner_id)
        return self._get_partner_information(pos_config, partner)  # 'res.partner': [] when not verified

    @http.route('/pos-self-order/get-partner-by-barcode', auth='public', type='jsonrpc', website=True)
    def get_partner(self, access_token, partner_barcode):
        pos_config = self._verify_pos_config(access_token)
        if pos_config.self_ordering_mode != "kiosk":
            raise Unauthorized('Invalid device type')
        if not partner_barcode or not isinstance(partner_barcode, str):
            return {}  # searching an empty barcode would match the customers who have none
        partner = pos_config.env['res.partner'].search([('barcode', '=', partner_barcode)], limit=1)
        return self._get_partner_information(pos_config, partner) if partner else {}

    @http.route('/pos-self-order/get-partner-by-mail', auth='public', type='jsonrpc', website=True)
    def get_partner_by_mail(self, access_token, mail):
        """Email an identification code to `mail`.

        The answer is the same whether a customer exists with this email or not, so that
        nobody can find out who the customers are.
        """
        pos_config = self._verify_pos_config(access_token)
        mail = email_normalize(mail)
        if not mail:
            raise UserError(self.env._('Email address is invalid.'))
        Otp = pos_config.env['pos_self_order_loyalty.otp']
        if Otp._is_email_blocked(mail, pos_config.company_id):
            return {'code_sent': False, 'too_many_attempts': True}
        Otp._send_code(mail, pos_config.company_id)
        return {'code_sent': True}

    @http.route('/pos-self-order/validate-partner-code', auth='public', type='jsonrpc', website=True)
    def validate_partner_code(self, access_token, mail, code):
        pos_config = self._verify_pos_config(access_token)
        mail = email_normalize(mail)
        if not mail:
            raise UserError(self.env._('Email address is invalid.'))
        if not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
            raise UserError(self.env._('Invalid verification code.'))
        Otp = pos_config.env['pos_self_order_loyalty.otp']
        if not Otp._check_code(mail, pos_config.company_id, code):
            return {'res.partner': [], 'too_many_attempts': Otp._is_email_blocked(mail, pos_config.company_id)}
        return self._get_partner_information(pos_config, self._get_or_create_partner_by_mail(pos_config, mail))

    def _get_or_create_partner_by_mail(self, pos_config, mail):
        """The customer owning `mail`, created now that the code proved the email is theirs."""
        # email_normalized also matches "Alice <Alice@Example.com>"; the oldest one wins
        # when several share the address, so a customer always gets the same account back
        partner = pos_config.env['res.partner'].search([('email_normalized', '=', mail)], order='id', limit=1)
        if partner:
            return partner
        # The self-order user isn't allowed to create contacts, as in validate_partner
        return pos_config.env['res.partner'].sudo().create({
            'name': mail,
            'email': mail,
            'company_id': pos_config.company_id.id,
        }).sudo(False)

    @http.route('/pos-self-order/check-card-code', auth='public', type='jsonrpc', website=True)
    def check_card_code(self, access_token, code, partner_id=None):
        # The card can either be a loyalty card or a loyalty rule with code
        # We first check the loyalty rule with code, if it exists we create a loyalty card for it
        # We then check all the loyalty cards and return the corresponding ones
        pos_config = self._verify_pos_config(access_token)

        # The partner is only trusted when its id was signed by the server
        partner = pos_config.env['pos.order']._get_self_partner_from_token(pos_config, partner_id) or pos_config.env['res.partner']

        # Check loyalty rules
        program_ids = pos_config._get_program_ids()
        corresponding_rule_id = program_ids.rule_ids.filtered_domain([('mode', '=', 'with_code'), ('code', '=', code)])
        corresponding_card_id = False
        corresponding_program_id = False
        reason = 'invalid_code'
        if corresponding_rule_id:
            # Testing code based on rule (discount code)
            # corresponding_rule_ids should be at most 1 due to unique constraint on code
            corresponding_program_id = corresponding_rule_id.program_id
        elif corresponding_card_id := pos_config.env['loyalty.card'].search([
            ('program_id', 'in', program_ids.ids),
            ('code', '=', code),
            '|', ('expiration_date', '=', False), ('expiration_date', '>=', fields.Date.context_today(pos_config)),
        ], limit=1):
            # Testing code based on loyalty cards (fidelity cards, gift cards, etc.)
            # corresponding_card_id should be at most 1 due to unique constraint on code
            if corresponding_card_id.partner_id and corresponding_card_id.partner_id != partner:
                reason = 'invalid_partner'
                corresponding_card_id = False  # card does not belong to the given partner
            if corresponding_card_id and corresponding_card_id.program_id.reward_ids and corresponding_card_id.points < min(corresponding_card_id.program_id.reward_ids.mapped('required_points')):
                reason = 'not_enough_points'
                corresponding_card_id = False  # if the card has not enough points for any rewards, we ignore it
            corresponding_program_id = corresponding_card_id.program_id if corresponding_card_id else False

        if not corresponding_program_id:
            return {
                'status': False,
                'reason': reason,
                'data': {'loyalty.program': [], 'loyalty.card': [], 'loyalty.rule': [], 'loyalty.reward': []}
            }

        if corresponding_program_id.limit_usage and corresponding_program_id.total_order_count >= corresponding_program_id.max_usage:
            return {'status': False, 'data': {'loyalty.program': [], 'loyalty.card': [], 'loyalty.rule': [], 'loyalty.reward': []}}

        reward_ids = corresponding_program_id.reward_ids.filtered_domain(self.env['loyalty.reward']._get_active_products_domain())
        product_read = self._add_product_linked_to_reward(reward_ids, pos_config)
        rules = pos_config.env['loyalty.rule']._load_pos_self_data_read(corresponding_program_id.rule_ids, pos_config)
        if corresponding_rule_id:
            # Codes aren't loaded in self-order (anyone could read them): the client needs
            # this one to apply it, and proved it knows it
            for rule in rules:
                if rule['id'] == corresponding_rule_id.id:
                    rule['code'] = corresponding_rule_id.code

        return {
            'status': True,
            'data': {
                **product_read,
                'loyalty.program': pos_config.env['loyalty.program']._load_pos_self_data_read(corresponding_program_id, pos_config),
                'loyalty.card': self._read_self_order_cards(pos_config, corresponding_card_id, partner) if corresponding_card_id else [],
                'loyalty.rule': rules,
                'loyalty.reward': pos_config.env['loyalty.reward']._load_pos_self_data_read(reward_ids, pos_config),
            },
        }

    def _generate_return_values(self, order, config):
        result = super()._generate_return_values(order, config)
        # The client knows the delivery addresses by their signed id only
        orders_by_id = {o.id: o for o in order}
        for order_data in result['pos.order']:
            pos_order = orders_by_id[order_data['id']]
            if pos_order.delivery_partner_id:
                order_data['delivery_partner_id'] = pos_order._get_signed_self_address_id(
                    config, pos_order.partner_id, pos_order.delivery_partner_id,
                )
        return result

    def _read_self_delivery_addresses(self, pos_config, partner, addresses):
        """Data of the delivery addresses of the identified customer `partner`, with signed ids."""
        addresses_data = pos_config.env['res.partner']._load_pos_self_data_read(addresses, pos_config)
        for address_data in addresses_data:
            address = addresses.browse(address_data['id'])
            address_data['id'] = pos_config.env['pos.order']._get_signed_self_address_id(pos_config, partner, address)
        return addresses_data

    @http.route('/pos-self-order/get-delivery-addresses', auth='public', type='jsonrpc', website=True)
    def get_delivery_addresses(self, access_token, partner_id):
        """The addresses the identified customer (signed id) can get an order delivered to."""
        pos_config = self._verify_pos_config(access_token)
        POSOrder = pos_config.env['pos.order']
        partner = POSOrder._get_self_partner_from_token(pos_config, partner_id)
        if not partner:
            return {'res.partner': []}
        addresses = POSOrder._get_self_delivery_addresses(partner).filtered(lambda a: a.street or a.street2)
        return {'res.partner': self._read_self_delivery_addresses(pos_config, partner, addresses)}

    @http.route('/pos-self-order/archive-delivery-address', auth='public', type='jsonrpc', website=True)
    def archive_delivery_address(self, access_token, partner_id, delivery_partner_id):
        """Remove a delivery address of the identified customer, never their own contact."""
        pos_config = self._verify_pos_config(access_token)
        POSOrder = pos_config.env['pos.order']
        partner = POSOrder._get_self_partner_from_token(pos_config, partner_id)
        address = POSOrder._get_self_delivery_address(pos_config, partner, delivery_partner_id)
        if not address or address == partner:
            raise Forbidden()
        address.action_archive()
        return True

    @http.route()
    def validate_partner(self, access_token, name=None, phone=None, street=None, zip=None, city=None, country_id=None,
                         state_id=None, partner_id=None, email=None, preset_id=None, delivery_partner_id=None):
        """An identified customer (signed partner_id) stays the order's customer, with their
        loyalty: the order is delivered to one of their addresses (delivery_partner_id) or to
        the address they enter, instead of a new partner made from the form."""
        pos_config = self._verify_pos_config(access_token)
        POSOrder = pos_config.env['pos.order']
        partner = POSOrder._get_self_partner_from_token(pos_config, partner_id)
        preset = pos_config.env['pos.preset'].browse(int(preset_id)).exists() if preset_id else pos_config.env['pos.preset']
        if not partner or preset.identification != 'address':
            return super().validate_partner(
                access_token, name, phone, street, zip, city, country_id,
                state_id=state_id, partner_id=partner_id, email=email, preset_id=preset_id,
            )

        if delivery_partner_id:
            address = POSOrder._get_self_delivery_address(pos_config, partner, delivery_partner_id)
            if not address:
                return {'error': {'type': 'address', 'message': self.env._("This address isn't available anymore.")}}
        elif street:
            address = self._set_self_delivery_address(partner, {
                'name': name or False,
                'phone': phone or False,
                'street': street,
                'zip': zip or False,
                'city': city or False,
                'country_id': pos_config.env['res.country'].browse(int(country_id)).exists().id if country_id else False,
                'state_id': pos_config.env['res.country.state'].browse(int(state_id)).exists().id if state_id else False,
            })
        else:
            return {'error': {'type': 'address', 'message': self.env._("Please enter your address.")}}

        google_places_api_key = request.env['ir.config_parameter'].sudo().get_str('google_address_autocomplete.google_places_api_key') or None
        if google_places_api_key and preset.service_at == 'delivery':
            # The address is kept even when it's too far: it's still the customer's
            error = self._check_delivery_address_for_partner(preset, address)
            if error:
                return {'error': error}
        return {'res.partner': self._read_self_delivery_addresses(pos_config, partner, address)}

    def _set_self_delivery_address(self, partner, values):
        """The address of the customer `partner` matching `values`.

        Their own contact gets it when it has no address yet. Otherwise it's one of their
        delivery addresses, a new one if none matches.
        """
        partner = partner.sudo()  # the self-order user isn't allowed to write contacts
        if not partner.street and not partner.street2:
            contact_values = {key: values[key] for key in ('street', 'zip', 'city', 'country_id', 'state_id')}
            if not partner.phone:
                contact_values['phone'] = values['phone']
            if values['name'] and partner.name == partner.email:
                # named after their email when identified by it (see _get_or_create_partner_by_mail)
                contact_values['name'] = values['name']
            partner.write(contact_values)
            return partner
        for address in partner.env['pos.order']._get_self_delivery_addresses(partner):
            if self._is_same_self_address(address, values):
                return address
        return partner.env['res.partner'].create({**values, 'type': 'delivery', 'parent_id': partner.id})

    def _is_same_self_address(self, address, values):
        # as portal's _are_same_addresses: unset on both sides counts as the same
        ResPartner = address.env['res.partner']
        for key, value in values.items():
            current = ResPartner._fields[key].convert_to_cache(address[key], ResPartner)
            if value != current and (value or current):
                return False
        return True

    def _add_product_linked_to_reward(self, reward_ids, pos_config):
        product_read = pos_config.env['product.template'].load_product_from_pos(pos_config.id, [('product_variant_ids', 'in', reward_ids.discount_line_product_id.ids + reward_ids.reward_product_ids.ids)])
        self_models = pos_config._load_self_data_models()
        keys_to_remove = [model_key for model_key in product_read if model_key not in self_models]
        for key in keys_to_remove:
            del product_read[key]
        return product_read
