# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError

class PosConfig(models.Model):
    _inherit = 'pos.config'

    gift_card_settings = fields.Selection(
        [
            ("create_set", "Generate PDF cards"),
            ("scan_use", "Scan existing cards"),
        ],
        string="Gift Cards settings",
        default="create_set",
        help="Defines the way you want to set your gift cards.",
    )
    # NOTE: this funtions acts as a m2m field with loyalty.program model. We do this to handle an excpetional use case:
    # When no PoS is specified at a loyalty program form, this program is applied to every PoS (instead of none)
    def _get_program_ids(self):
        return self.env['loyalty.program'].search(['&', ('pos_ok', '=', True), '|', ('pos_config_ids', '=', self.id), ('pos_config_ids', '=', False)])

    def _check_before_creating_new_session(self):
        self.ensure_one()
        # Check validity of programs before opening a new session
        invalid_reward_products_msg = ''
        for reward in self._get_program_ids().reward_ids:
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
        gift_card_programs = self._get_program_ids().filtered(lambda p: p.program_type == 'gift_card')
        for product in gift_card_programs.mapped('rule_ids.valid_product_ids'):
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
        if gift_card_programs:
            for gc_program in gift_card_programs:
                # Do not allow a gift card program with more than one rule or reward, and check that they make sense
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
                if self.gift_card_settings == "create_set":
                    if not gc_program.mail_template_id:
                        raise UserError(_('There is no email template on the gift card program and your pos is set to print them.'))
                    if not gc_program.pos_report_print_id:
                        raise UserError(_('There is no print report on the gift card program and your pos is set to print them.'))

        return super()._check_before_creating_new_session()

    def use_coupon_code(self, code, creation_date, partner_id):
        self.ensure_one()
        # Ordering by partner id to use the first assigned to the partner in case multiple coupons have the same code
        #  it could happen with loyalty programs using a code
        # Points desc so that in coupon mode one could use a coupon multiple times
        coupon = self.env['loyalty.card'].search(
            [('program_id', 'in', self._get_program_ids().ids), ('partner_id', 'in', (False, partner_id)), ('code', '=', code)],
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
            (coupon.program_id.date_to and coupon.program_id.date_to < fields.Date.context_today(self)) or\
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
                'has_source_order': coupon._has_source_order(),
            },
        }
