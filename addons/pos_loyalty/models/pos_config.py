# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

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
        for product in gift_card_programs.rule_ids.valid_product_ids:
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
            raise UserError(f"{prefix_error_msg}\n{invalid_reward_products_msg}")  # pylint: disable=missing-gettext
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
                if not gc_program.mail_template_id:
                    raise UserError(_('There is no email template on the gift card program and your pos is set to print them.'))
                if not gc_program.pos_report_print_id:
                    raise UserError(_('There is no print report on the gift card program and your pos is set to print them.'))

        return super()._check_before_creating_new_session()

    def use_coupon_code(self, code, creation_date, partner_id, pricelist_id):
        self.ensure_one()
        # Points desc so that in coupon mode one could use a coupon multiple times
        coupon = self.env['loyalty.card'].search(
            [('program_id', 'in', self._get_program_ids().ids),
             '|', ('partner_id', 'in', (False, partner_id)), ('program_type', '=', 'gift_card'),
             ('code', '=', code)],
            order='partner_id, points desc', limit=1)
        program = coupon.program_id
        if not coupon or not program.active:
            return {
                'successful': False,
                'payload': {
                    'error_message': _('This coupon is invalid (%s).', code),
                },
            }
        check_date = fields.Date.from_string(creation_date[:11])
        today_date = fields.Date.context_today(self)
        error_message = False
        if (
            (coupon.expiration_date and coupon.expiration_date < check_date)
            or (program.date_to and program.date_to < today_date)
            or (program.limit_usage and program.total_order_count >= program.max_usage)
        ):
            error_message = _("This coupon is expired (%s).", code)
        elif program.date_from and program.date_from > today_date:
            error_message = _("This coupon is not yet valid (%s).", code)
        elif (
            not program.reward_ids or
            not any(r.required_points <= coupon.points for r in program.reward_ids)
        ):
            error_message = _("No reward can be claimed with this coupon.")
        elif program.pricelist_ids and pricelist_id not in program.pricelist_ids.ids:
            error_message = _("This coupon is not available with the current pricelist.")

        if error_message:
            return {
                'successful': False,
                'payload': {
                    'error_message': error_message,
                },
            }

        return {
            'successful': True,
            'payload': {
                'program_id': program.id,
                'coupon_id': coupon.id,
                'coupon_partner_id': coupon.partner_id.id,
                'points': coupon.points,
                'has_source_order': coupon._has_source_order(),
            },
        }
