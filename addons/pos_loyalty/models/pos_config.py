# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_loyalty_program(self):
        return self.env['loyalty.program'].search([('program_type', '=', 'loyalty')], limit=1)

    use_coupon_programs = fields.Boolean('Coupons & Promotions',
        help="Use coupon and promotion programs in this PoS configuration.")
    coupon_program_ids = fields.Many2many(
        'loyalty.program', string="Coupon Programs", domain=[('pos_ok', '=', True), ('program_type', '=', 'coupons')],
        relation='pos_config_coupon_program_rel')
    promo_program_ids = fields.Many2many(
        'loyalty.program', string="Promotion Programs", domain=[('pos_ok', '=', True), ('program_type', 'in', ('promotion', 'buy_x_get_y', 'promo_code', 'next_order_coupons'))],
        relation='pos_config_promo_program_rel')

    loyalty_program_id = fields.Many2one('loyalty.program', "PoS Loyalty Programs", domain=[('pos_ok', '=', True), ('program_type', '=', 'loyalty')], default=_default_loyalty_program)

    use_gift_card = fields.Boolean('Gift Cards')
    gift_card_program_id = fields.Many2one('loyalty.program', "PoS Gift Card Program", domain=[('pos_ok', '=', True), ('program_type', '=', 'gift_card')])
    gift_card_settings = fields.Selection(
        [
            ("create_set", "Generate a new barcode and set a price"),
            ("scan_set", "Scan an existing barcode and set a price"),
            ("scan_use", "Scan an existing barcode with an existing price"),
        ],
        string="Gift Cards settings",
        default="create_set",
        help="Defines the way you want to set your gift cards.",
    )

    # While we select all program types separately they will all behave the same
    all_program_ids = fields.Many2many('loyalty.program', compute='_compute_all_programs')

    @api.depends('use_coupon_programs', 'coupon_program_ids', 'promo_program_ids',
        'loyalty_program_id', 'use_gift_card', 'gift_card_program_id')
    def _compute_all_programs(self):
        for config in self:
            programs = self.env['loyalty.program']
            if config.use_coupon_programs:
                programs |= config.coupon_program_ids
                programs |= config.promo_program_ids
            # This may be a separate field on the config but it actually will be handled just like any other program
            if config.loyalty_program_id:
                programs |= config.loyalty_program_id
            # We also include the gift card program to be able to claim the reward (discount)
            # This one will behave a little differently as it will display more options
            if config.use_gift_card:
                programs |= config.gift_card_program_id
            config.all_program_ids = programs

    @api.model
    def set_loyalty_program_to_main_config(self):
        main_config = self.env.ref('point_of_sale.pos_config_main')
        default_loyalty_program = self._default_loyalty_program()
        main_config.write({'module_pos_loyalty': bool(default_loyalty_program), 'loyalty_program_id': default_loyalty_program.id})

    def _check_before_creating_new_session(self):
        self.ensure_one()
        # Check validity of programs before opening a new session
        invalid_reward_products_msg = ''
        for reward in self.all_program_ids.reward_ids:
            if reward.reward_type == 'product':
                for product in reward.reward_product_ids:
                    if product.available_in_pos:
                        continue
                    invalid_reward_products_msg += "\n\t"
                    invalid_reward_products_msg += _(
                        "Program: %(name)s, Reward Product: `%(reward_product)s`",
                        name=reward.program_id.name,
                        reward_product=product.name,
                    )
        if self.gift_card_program_id:
            for product in self.gift_card_program_id.rule_ids.valid_product_ids:
                if product.available_in_pos:
                    continue
                invalid_reward_products_msg += "\n\t"
                invalid_reward_products_msg += _(
                    "Program: %(name)s, Rule Product: `%(rule_product)s`",
                    name=reward.program_id.name,
                    rule_product=product.name,
                )

        if invalid_reward_products_msg:
            prefix_error_msg = _("To continue, make the following reward products available in Point of Sale.")
            raise UserError(f"{prefix_error_msg}\n{invalid_reward_products_msg}")
        if self.use_gift_card and self.gift_card_program_id:
            # Do not allow gift_card_program_id with more than one rule or reward, and check that they make sense
            gc_program = self.gift_card_program_id
            if len(gc_program.reward_ids) > 1:
                raise UserError(_('Invalid gift card program. More than one reward.'))
            elif len(gc_program.rule_ids) > 1:
                raise UserError(_('Invalid gift card program. More than one rule.'))
            rule = gc_program.rule_ids
            if rule.reward_point_amount != 1 or rule.reward_point_mode != 'money':
                raise UserError(_('Invalid gift card program rule. Use 1 point per currency spent.'))
            reward = gc_program.reward_ids
            if reward.reward_type != 'discount' or reward.discount_mode != 'per_point' or reward.discount != 1:
                raise UserError(_('Invalid gift card program reward. Use 1 currency per point discount.'))
        return super()._check_before_creating_new_session()

    def use_coupon_code(self, code, creation_date, partner_id):
        self.ensure_one()
        # Ordering by partner id to use the first assigned to the partner in case multiple coupons have the same code
        #  it could happen with loyalty programs using a code
        # Points desc so that in coupon mode one could use a coupon multiple times
        coupon = self.env['loyalty.card'].search(
            [('program_id', 'in', self.all_program_ids.ids), ('partner_id', 'in', (False, partner_id)), ('code', '=', code)],
            order='partner_id, points desc', limit=1)
        if not coupon or not coupon.program_id.active:
            return {
                'successful': False,
                'payload': {
                    'error_message': _('This coupon is invalid (%s).', code),
                },
            }
        check_date = fields.Date.from_string(creation_date[:11])
        if (coupon.expiration_date and coupon.expiration_date < check_date) or\
            (coupon.program_id.date_to and coupon.program_id.date_to <= fields.Date.context_today(self)) or\
            (coupon.program_id.limit_usage and coupon.program_id.total_order_count >= coupon.program_id.max_usage):
            return {
                'successful': False,
                'payload': {
                    'error_message': _('This coupon is expired (%s).', code),
                },
            }
        if not coupon.program_id.reward_ids or not any(reward.required_points <= coupon.points for reward in coupon.program_id.reward_ids):
            return {
                'successful': False,
                'payload': {
                    'error_message': _('No reward can be claimed with this coupon.'),
                },
            }
        return {
            'successful': True,
            'payload': {
                'program_id': coupon.program_id.id,
                'coupon_id': coupon.id,
                'coupon_partner_id': coupon.partner_id.id,
                'points': coupon.points,
            },
        }
