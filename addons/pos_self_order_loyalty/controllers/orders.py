from odoo import fields, http
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from odoo.tools.mail import email_normalize
from odoo.exceptions import UserError
from odoo.addons.pos_self_order_loyalty.models.res_partner import SelfOrderIdentificationExpired
import re


class PosSelfOrderControllerLoyalty(PosSelfOrderController):
    def _get_partner_information(self, pos_config, partner):
        today = fields.Date.context_today(self)
        loyalty_programs = pos_config._get_program_ids().filtered(lambda p: p.program_type in ['loyalty', 'ewallet'])
        loyalty_cards = loyalty_programs.coupon_ids.filtered(
            lambda c: c.partner_id == partner and not (c.expiration_date and c.expiration_date < today)
        )
        reward_ids = loyalty_cards.program_id.reward_ids.filtered_domain(pos_config.env['loyalty.reward']._get_active_products_domain())
        product_read = self._add_product_linked_to_reward(reward_ids, pos_config)
        if len(partner):
            return {
                **product_read,
                'res.partner': pos_config.env['res.partner']._load_pos_self_data_read_with_token(partner, pos_config),
                'loyalty.card': pos_config.env['loyalty.card']._load_pos_self_data_read(loyalty_cards, pos_config),
                'loyalty.rule': pos_config.env['loyalty.rule']._load_pos_self_data_read(loyalty_cards.program_id.rule_ids, pos_config),
                'loyalty.reward': pos_config.env['loyalty.reward']._load_pos_self_data_read(reward_ids, pos_config),
                'loyalty.program': pos_config.env['loyalty.program']._load_pos_self_data_read(loyalty_cards.program_id, pos_config),
            }
        return {
            **product_read,
            'res.partner': [],
            'loyalty.card': [],
            'loyalty.rule': [],
            'loyalty.reward': [],
            'loyalty.program': [],
        }

    @http.route()
    def process_order(self, order, access_token, table_identifier, device_type):
        result = super().process_order(order, access_token, table_identifier, device_type)
        # Slide the identification: the partner was verified by pos.order._check_pos_order
        pos_config = self._verify_pos_config(access_token)
        partner = pos_config.env['res.partner']._get_partner_from_self_order_token(
            pos_config, order.get('partner_id'), order.get('partner_token'),
        )
        if partner:
            result['res.partner'] = pos_config.env['res.partner']._load_pos_self_data_read_with_token(partner, pos_config)
        return result

    @http.route()
    def validate_partner(self, access_token, name, phone, street, zip, city, country_id, state_id=None, partner_id=None, email=None, preset_id=None):
        result = super().validate_partner(
            access_token, name, phone, street, zip, city, country_id,
            state_id=state_id, partner_id=partner_id, email=email, preset_id=preset_id,
        )
        # Only a partner created by this very call is proven to belong to the client;
        # an existing partner_id is just a number the client sent
        if not partner_id and result.get('res.partner'):
            pos_config = self._verify_pos_config(access_token)
            partner = pos_config.env['res.partner'].browse(result['res.partner'][0]['id'])
            result['res.partner'][0]['_self_order_token'] = partner._get_self_order_token(pos_config)
        return result

    @http.route('/pos-self-order/refresh-partner-token', auth='public', type='jsonrpc', website=True)
    def refresh_partner_token(self, access_token, partner_id, partner_token):
        """Renew a stored identification, along with the partner's up-to-date loyalty data."""
        pos_config = self._verify_pos_config(access_token)
        partner = pos_config.env['res.partner']._get_partner_from_self_order_token(pos_config, partner_id, partner_token)
        return self._get_partner_information(pos_config, partner)  # 'res.partner': [] when invalid

    @http.route('/pos-self-order/get-partner-by-barcode', auth='public', type='jsonrpc', website=True)
    def get_partner(self, access_token, partner_barcode):
        pos_config = self._verify_pos_config(access_token)
        partner = pos_config.env['res.partner'].search([('barcode', '=', partner_barcode)], limit=1)
        return self._get_partner_information(pos_config, partner) if partner else {}

    @http.route('/pos-self-order/get-partner-by-mail', auth='public', type='jsonrpc', website=True)
    def get_partner_by_mail(self, access_token, mail):
        pos_config = self._verify_pos_config(access_token)
        new = False
        mail = email_normalize(mail)
        if not mail:
            raise UserError(self.env._('Email address is invalid.'))

        partner = pos_config.env['res.partner'].search([('email', '=', mail)], limit=1)
        if not partner:
            partner = pos_config.env['res.partner'].create({
                'name': mail,
                'email': mail,
                'is_company': False,
                'company_id': pos_config.company_id.id,
            })
            new = True
        else:
            partner._send_code_to_client()
            partner = False
        return {
            'new': new,
            'data': {
                'res.partner': pos_config.env['res.partner']._load_pos_self_data_read_with_token(partner, pos_config) if partner else [],
            },
        }

    @http.route('/pos-self-order/validate-partner-code', auth='public', type='jsonrpc', website=True)
    def validate_partner_code(self, access_token, mail, code):
        pos_config = self._verify_pos_config(access_token)
        mail = email_normalize(mail)
        if not mail:
            raise UserError(self.env._('Email address is invalid.'))
        if not bool(re.fullmatch(r"\d{6}", code)):
            raise UserError(self.env._('Invalid verification code.'))
        partner = pos_config.env['res.partner'].search([('email', '=', mail)], limit=1)
        if partner and partner._validate_code(code):
            return self._get_partner_information(pos_config, partner)
        return {'res.partner': []}

    @http.route('/pos-self-order/check-card-code', auth='public', type='jsonrpc', website=True)
    def check_card_code(self, access_token, code, partner_id=None, partner_token=None, order_uuid=None):
        # The card can either be a loyalty card or a loyalty rule with code
        # We first check the loyalty rule with code, if it exists we create a loyalty card for it
        # We then check all the loyalty cards and return the corresponding ones
        pos_config = self._verify_pos_config(access_token)

        # Get partner, only trusted when backed by its identification token
        partner = None
        if partner_id:
            partner = pos_config.env['res.partner']._get_partner_from_self_order_token(pos_config, partner_id, partner_token)
            if not partner:
                raise SelfOrderIdentificationExpired(self.env._("Your identification has expired, please identify yourself again."))

        # Check loyalty rules
        program_ids = pos_config._get_program_ids()
        corresponding_rule_id = False
        corresponding_card_id = False
        corresponding_program_id = False
        reason = 'invalid_code'
        if corresponding_rule_id := program_ids.rule_ids.filtered_domain([('mode', '=', 'with_code'), ('code', '=', code)]):
            # Testing code based on rule (discount code)
            # corresponding_rule_ids should be at most 1 due to unique constraint on code
            corresponding_program_id = corresponding_rule_id.program_id
        elif corresponding_card_id := program_ids.coupon_ids.filtered_domain([('code', '=', code), '|', ('expiration_date', '=', False), ('expiration_date', '>=', fields.Date.context_today(pos_config))]):
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

        # Lock the loyalty program row to block several processes that try to
        # read it at the same time. We also use NOWAIT to make sure we trigger a
        # serialization error when the processes don't have the lock and thus,
        # trigger a retry of the transaction.
        self.env.cr.execute("""
            SELECT id FROM loyalty_program WHERE id=%s FOR UPDATE NOWAIT
        """, (corresponding_program_id.id,))

        if corresponding_program_id.limit_usage and corresponding_program_id.total_order_count >= corresponding_program_id.max_usage:
            return {'status': False, 'data': {'loyalty.program': [], 'loyalty.card': [], 'loyalty.rule': [], 'loyalty.reward': []}}

        reward_ids = corresponding_program_id.reward_ids.filtered_domain(self.env['loyalty.reward']._get_active_products_domain())
        product_read = self._add_product_linked_to_reward(reward_ids, pos_config)

        return {
            'status': True,
            'data': {
                **product_read,
                'loyalty.program': pos_config.env['loyalty.program']._load_pos_self_data_read(corresponding_program_id, pos_config),
                'loyalty.card': pos_config.env['loyalty.card']._load_pos_self_data_read(corresponding_card_id, pos_config) if corresponding_card_id else [],
                'loyalty.rule': pos_config.env['loyalty.rule']._load_pos_self_data_read(corresponding_program_id.rule_ids, pos_config),
                'loyalty.reward': pos_config.env['loyalty.reward']._load_pos_self_data_read(reward_ids, pos_config),
            },
        }

    def _add_product_linked_to_reward(self, reward_ids, pos_config):
        product_read = pos_config.env['product.template'].load_product_from_pos(pos_config.id, [('product_variant_ids', 'in', reward_ids.discount_line_product_id.ids + reward_ids.reward_product_ids.ids)])
        keys_to_remove = []
        self_models = pos_config._load_self_data_models()
        for model_key in product_read:
            if model_key not in self_models:
                keys_to_remove.append(model_key)
        for key in keys_to_remove:
            del product_read[key]
        return product_read
