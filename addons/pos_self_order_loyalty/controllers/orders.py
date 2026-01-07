from odoo import fields, http
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosSelfOrderControllerLoyalty(PosSelfOrderController):
    @http.route('/pos-self-order/process-loyalty-cards', auth='public', type='jsonrpc', website=True)
    def process_loyalty_cards(self, access_token, serialized_cards):
        pos_config = self._verify_pos_config(access_token)
        # Process the loyalty cards here
        # set the points to 0 everytime
        try:
            for card in serialized_cards:
                card['code'] = pos_config.env['loyalty.card']._generate_code() if not card['code'] else card['code']
                card['points'] = 0
            cards = pos_config.env['loyalty.card'].create(serialized_cards)
        except Exception:
            return {'loyalty.card': []}
        return {'loyalty.card': pos_config.env['loyalty.card']._load_pos_self_data_read(cards, pos_config) if len(cards) else []}

    @http.route('/pos-self-order/get-partner-by-barcode', auth='public', type='jsonrpc', website=True)
    def get_partner(self, access_token, partner_barcode):
        pos_config = self._verify_pos_config(access_token)
        partner = pos_config.env['res.partner'].search([('barcode', '=', partner_barcode)], limit=1)
        loyalty_cards = pos_config._get_program_ids().filtered(lambda p: p.program_type == 'loyalty').coupon_ids.filtered(lambda c: c.partner_id == partner and not (c.expiration_date and c.expiration_date < fields.Date.context_today(self)))
        # Adding eWallet linked to the partner
        loyalty_cards |= pos_config.env['loyalty.program'].search([('program_type', '=', 'ewallet')]).coupon_ids.filtered(lambda c: c.partner_id == partner and not (c.expiration_date and c.expiration_date < fields.Date.context_today(self)))
        reward_ids = loyalty_cards.program_id.reward_ids.filtered_domain(pos_config.env['loyalty.reward']._get_active_products_domain())
        product_read = self._add_product_linked_to_reward(reward_ids, pos_config)
        return {
            **product_read,
            'res.partner': pos_config.env['res.partner']._load_pos_self_data_read(partner, pos_config) if len(partner) else [],
            'loyalty.card': pos_config.env['loyalty.card']._load_pos_self_data_read(loyalty_cards, pos_config) if len(partner) else [],
            'loyalty.rule': pos_config.env['loyalty.rule']._load_pos_self_data_read(loyalty_cards.program_id.rule_ids, pos_config) if len(partner) else [],
            'loyalty.reward': pos_config.env['loyalty.reward']._load_pos_self_data_read(reward_ids, pos_config) if len(partner) else [],
            'loyalty.program': pos_config.env['loyalty.program']._load_pos_self_data_read(loyalty_cards.program_id, pos_config) if len(partner) else [],
        }

    @http.route('/pos-self-order/check-coupon-code', auth='public', type='jsonrpc', website=True)
    def check_coupon_code(self, access_token, coupon_code, partner_id=None, order_uuid=None):
        # The coupon can either be a loyalty card or a loyalty rule with code
        # We first check the loyalty rule with code, if it exists we create a loyalty card for it
        # We then check all the loyalty cards and return the corresponding ones
        pos_config = self._verify_pos_config(access_token)

        # Get partner
        partner = pos_config.env['res.partner'].browse(partner_id).exists() if partner_id else None

        # Check loyalty rules
        program_ids = pos_config._get_program_ids()
        corresponding_rule_id = False
        corresponding_coupon_id = False
        corresponding_program_id = False
        if corresponding_rule_id := program_ids.rule_ids.filtered_domain([('mode', '=', 'with_code'), ('code', '=', coupon_code)]):
            # Testing code based on rule (discount code)
            # corresponding_rule_ids should be at most 1 due to unique constraint on code
            corresponding_program_id = corresponding_rule_id.program_id
            # If there is already a loyalty card for this program and order, we use it instead of creating a new one
            if coupon_ids := corresponding_program_id.coupon_ids.filtered(lambda c: (not c.expiration_date or c.expiration_date >= fields.Date.context_today(self)) and c.source_pos_order_uuid == order_uuid):
                corresponding_coupon_id = coupon_ids[0]
            else:
                corresponding_coupon_id = pos_config.env['loyalty.card'].create({
                    'program_id': corresponding_program_id.id,
                    'points': corresponding_rule_id.reward_point_amount,
                    'partner_id': partner.id if partner else None,
                    'source_pos_order_uuid': order_uuid,
                })
        elif corresponding_coupon_id := pos_config.env['loyalty.card'].search([('code', '=', coupon_code), '|', ('expiration_date', '=', False), ('expiration_date', '>=', fields.Date.context_today(self))]):
            # Testing code based on loyalty cards (fidelity cards, gift cards, etc.)
            # corresponding_coupon_id should be at most 1 due to unique constraint on code
            if corresponding_coupon_id.partner_id and partner and corresponding_coupon_id.partner_id != partner:
                corresponding_coupon_id = False  # coupon does not belong to the given partner
            if corresponding_coupon_id and corresponding_coupon_id.points < min(corresponding_coupon_id.program_id.reward_ids.mapped('required_points')):
                corresponding_coupon_id = False  # if the coupon has not enough points for any rewards, we ignore it
            corresponding_program_id = corresponding_coupon_id.program_id if corresponding_coupon_id else False

        if not corresponding_program_id:
            return {'loyalty.program': [], 'loyalty.card': [], 'loyalty.rule': [], 'loyalty.reward': []}

        # Lock the loyalty program row to block several processes that try to
        # read it at the same time. We also use NOWAIT to make sure we trigger a
        # serialization error when the processes don't have the lock and thus,
        # trigger a retry of the transaction.
        self.env.cr.execute("""
            SELECT id FROM loyalty_program WHERE id=%s FOR UPDATE NOWAIT
        """, (corresponding_program_id.id,))

        if corresponding_program_id.limit_usage and corresponding_program_id.total_order_count >= corresponding_program_id.max_usage:
            return {'loyalty.program': [], 'loyalty.card': [], 'loyalty.rule': [], 'loyalty.reward': []}

        reward_ids = corresponding_program_id.reward_ids.filtered_domain(self.env['loyalty.reward']._get_active_products_domain()).filtered(lambda r: r.required_points <= (corresponding_coupon_id.points if corresponding_coupon_id else 0))
        product_read = self._add_product_linked_to_reward(reward_ids, pos_config)

        return {
            **product_read,
            'loyalty.program': pos_config.env['loyalty.program']._load_pos_self_data_read(corresponding_program_id, pos_config),
            'loyalty.card': pos_config.env['loyalty.card']._load_pos_self_data_read(corresponding_coupon_id, pos_config),
            'loyalty.reward': pos_config.env['loyalty.reward']._load_pos_self_data_read(reward_ids, pos_config),
        }

    def _verify_line_price(self, lines, pos_config, preset_id):
        super()._verify_line_price(lines, pos_config, preset_id)
        # In case of a reward line, we need to make sure that the user can use it
        lines.order_id._verify_coupon_validity()

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
