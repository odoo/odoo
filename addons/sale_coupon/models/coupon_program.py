# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CouponProgram(models.Model):
    _inherit = 'coupon.program'

    order_count = fields.Integer(compute='_compute_order_count')

    # The api.depends is handled in `def modified` of `sale_coupon/models/sale_order.py`
    def _compute_order_count(self):
        product_data = self.env['sale.order.line'].read_group([('product_id', 'in', self.mapped('discount_line_product_id').ids)], ['product_id'], ['product_id'])
        mapped_data = dict([(m['product_id'][0], m['product_id_count']) for m in product_data])
        for program in self:
            program.order_count = mapped_data.get(program.discount_line_product_id.id, 0)

    def action_view_sales_orders(self):
        self.ensure_one()
        orders = self.env['sale.order.line'].search([('product_id', '=', self.discount_line_product_id.id)]).mapped('order_id')
        return {
            'name': _('Sales Orders'),
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', orders.ids), ('state', 'not in', ('draft', 'sent', 'cancel'))],
            'context': dict(self._context, create=False)
        }

    def _check_promo_code(self, order, coupon_code):
        message = {}
        if self.maximum_use_number != 0 and self.order_count >= self.maximum_use_number:
            message = {'error': _('Promo code %s has been expired.') % (coupon_code)}
        elif not self._filter_on_mimimum_amount(order):
            message = {'error': _(
                'A minimum of %(amount)s %(currency)s should be purchased to get the reward',
                amount=self.rule_minimum_amount,
                currency=self.currency_id.name
            )}
        elif self.promo_code and self.promo_code == order.promo_code:
            message = {'error': _('The promo code is already applied on this order')}
        elif not self.promo_code and self in order.no_code_promo_program_ids:
            message = {'error': _('The promotional offer is already applied on this order')}
        elif not self.active:
            message = {'error': _('Promo code is invalid')}
        elif self.rule_date_from and self.rule_date_from > order.date_order or self.rule_date_to and order.date_order > self.rule_date_to:
            message = {'error': _('Promo code is expired')}
        elif order.promo_code and self.promo_code_usage == 'code_needed':
            message = {'error': _('Promotionals codes are not cumulative.')}
        elif self._is_global_discount_program() and order._is_global_discount_already_applied():
            message = {'error': _('Global discounts are not cumulative.')}
        elif self.promo_applicability == 'on_current_order' and self.reward_type == 'product' and not order._is_reward_in_order_lines(self):
            message = {'error': _('The reward products should be in the sales order lines to apply the discount.')}
        elif not self._is_valid_partner(order.partner_id):
            message = {'error': _("The customer doesn't have access to this reward.")}
        elif not self._filter_programs_on_products(order):
            message = {'error': _("You don't have the required product quantities on your sales order. If the reward is same product quantity, please make sure that all the products are recorded on the sales order (Example: You need to have 3 T-shirts on your sales order if the promotion is 'Buy 2, Get 1 Free'.")}
        elif self.promo_applicability == 'on_current_order' and not self.env.context.get('applicable_coupon'):
            applicable_programs = order._get_applicable_programs()
            if self not in applicable_programs:
                message = {'error': _('At least one of the required conditions is not met to get the reward!')}
        return message

    @api.model
    def _filter_on_mimimum_amount(self, order):
        no_effect_lines = order._get_no_effect_on_threshold_lines()
        order_amount = {
            'amount_untaxed' : order.amount_untaxed - sum(line.price_subtotal for line in no_effect_lines),
            'amount_tax' : order.amount_tax - sum(line.price_tax for line in no_effect_lines)
        }
        program_ids = list()
        for program in self:
            if program.reward_type != 'discount':
                # avoid the filtered
                lines = self.env['sale.order.line']
            else:
                lines = order.order_line.filtered(lambda line:
                    line.product_id == program.discount_line_product_id or
                    line.product_id == program.reward_id.discount_line_product_id or
                    (program.program_type == 'promotion_program' and line.is_reward_line)
                )
            untaxed_amount = order_amount['amount_untaxed'] - sum(line.price_subtotal for line in lines)
            tax_amount = order_amount['amount_tax'] - sum(line.price_tax for line in lines)
            program_amount = program._compute_program_amount('rule_minimum_amount', order.currency_id)
            if program.rule_minimum_amount_tax_inclusion == 'tax_included' and program_amount <= (untaxed_amount + tax_amount) or program_amount <= untaxed_amount:
                program_ids.append(program.id)

        return self.browse(program_ids)

    @api.model
    def _filter_on_validity_dates(self, order):
        return self.filtered(lambda program:
            (not program.rule_date_from or program.rule_date_from <= order.date_order)
            and
            (not program.rule_date_to or program.rule_date_to >= order.date_order)
        )

    @api.model
    def _filter_promo_programs_with_code(self, order):
        '''Filter Promo program with code with a different promo_code if a promo_code is already ordered'''
        return self.filtered(lambda program: program.promo_code_usage == 'code_needed' and program.promo_code != order.promo_code)

    def _filter_unexpired_programs(self, order):
        return self.filtered(lambda program: program.maximum_use_number == 0 or program.order_count <= program.maximum_use_number)

    def _filter_programs_on_partners(self, order):
        return self.filtered(lambda program: program._is_valid_partner(order.partner_id))

    def _filter_programs_on_products(self, order):
        """
        To get valid programs according to product list.
        i.e Buy 1 imac + get 1 ipad mini free then check 1 imac is on cart or not
        or  Buy 1 coke + get 1 coke free then check 2 cokes are on cart or not
        """
        order_lines = order.order_line.filtered(lambda line: line.product_id) - order._get_reward_lines()
        products = order_lines.mapped('product_id')
        products_qties = dict.fromkeys(products, 0)
        for line in order_lines:
            products_qties[line.product_id] += line.product_uom_qty
        valid_program_ids = list()
        for program in self:
            if not program.rule_products_domain:
                valid_program_ids.append(program.id)
                continue
            valid_products = program._get_valid_products(products)
            if not valid_products:
                # The program can be directly discarded
                continue
            ordered_rule_products_qty = sum(products_qties[product] for product in valid_products)
            # Avoid program if 1 ordered foo on a program '1 foo, 1 free foo'
            if program.promo_applicability == 'on_current_order' and \
               program.reward_type == 'product' and program._get_valid_products(program.reward_product_id):
                ordered_rule_products_qty -= program.reward_product_quantity
            if ordered_rule_products_qty >= program.rule_min_quantity:
                valid_program_ids.append(program.id)
        return self.browse(valid_program_ids)

    def _filter_not_ordered_reward_programs(self, order):
        """
        Returns the programs when the reward is actually in the order lines
        """
        programs = self.env['coupon.program']
        for program in self:
            if program.reward_type == 'product' and \
               not order.order_line.filtered(lambda line: line.product_id == program.reward_product_id):
                continue
            elif program.reward_type == 'discount' and program.discount_apply_on == 'specific_products' and \
               not order.order_line.filtered(lambda line: line.product_id in program.discount_specific_product_ids):
                continue
            programs |= program
        return programs

    @api.model
    def _filter_programs_from_common_rules(self, order, next_order=False):
        """ Return the programs if every conditions is met
            :param bool next_order: is the reward given from a previous order
        """
        programs = self
        # Minimum requirement should not be checked if the coupon got generated by a promotion program (the requirement should have only be checked to generate the coupon)
        if not next_order:
            programs = programs and programs._filter_on_mimimum_amount(order)
        if not self.env.context.get("no_outdated_coupons"):
            programs = programs and programs._filter_on_validity_dates(order)
        programs = programs and programs._filter_unexpired_programs(order)
        programs = programs and programs._filter_programs_on_partners(order)
        # Product requirement should not be checked if the coupon got generated by a promotion program (the requirement should have only be checked to generate the coupon)
        if not next_order:
            programs = programs and programs._filter_programs_on_products(order)

        programs_curr_order = programs.filtered(lambda p: p.promo_applicability == 'on_current_order')
        programs = programs.filtered(lambda p: p.promo_applicability == 'on_next_order')
        if programs_curr_order:
            # Checking if rewards are in the SO should not be performed for rewards on_next_order
            programs += programs_curr_order._filter_not_ordered_reward_programs(order)
        return programs

    def _get_discount_product_values(self):
        res = super()._get_discount_product_values()
        res['invoice_policy'] = 'order'
        return res

    def _is_global_discount_program(self):
        self.ensure_one()
        return self.promo_applicability == 'on_current_order' and \
               self.reward_type == 'discount' and \
               self.discount_type == 'percentage' and \
               self.discount_apply_on == 'on_order'

    def _keep_only_most_interesting_auto_applied_global_discount_program(self):
        '''Given a record set of programs, remove the less interesting auto
        applied global discount to keep only the most interesting one.
        We should not take promo code programs into account as a 10% auto
        applied is considered better than a 50% promo code, as the user might
        not know about the promo code.
        '''
        programs = self.filtered(lambda p: p._is_global_discount_program() and p.promo_code_usage == 'no_code_needed')
        if not programs: return self
        most_interesting_program = max(programs, key=lambda p: p.discount_percentage)
        # remove least interesting programs
        return self - (programs - most_interesting_program)
