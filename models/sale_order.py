# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    applied_coupon_ids = fields.One2many('sale.coupon', 'sales_order_id', string="Applied Coupons", copy=False)
    generated_coupon_ids = fields.One2many('sale.coupon', 'order_id', string="Offered Coupons", copy=False)
    reward_amount = fields.Float(compute='_compute_reward_total')
    no_code_promo_program_ids = fields.Many2many('sale.coupon.program', string="Applied Immediate Promo Programs",
        domain=[('promo_code_usage', '=', 'no_code_needed')], copy=False)
    code_promo_program_id = fields.Many2one('sale.coupon.program', string="Applied Promo Program",
        domain=[('promo_code_usage', '=', 'code_needed')], copy=False)
    promo_code = fields.Char(related='code_promo_program_id.promo_code', help="Applied program code")

    @api.depends('order_line')
    def _compute_reward_total(self):
        for order in self:
            order.reward_amount = sum([line.price_subtotal for line in order.order_line.filtered(lambda line: line.is_reward_line)])

    @api.multi
    def recompute_coupon_lines(self):
        for order in self:
            order._remove_invalid_reward_lines()
            order._create_new_no_code_promo_reward_lines()
            order._update_existing_reward_lines()

    def copy(self, default=None):
        order = super(SaleOrder, self).copy(dict(default or {}, order_line=False))
        for line in self.order_line.filtered(lambda line: not line.is_reward_line):
            line.copy({'order_id': order.id})
        order.with_context(sale_coupon_no_loop=False)._create_new_no_code_promo_reward_lines()
        return order

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.recompute_coupon_lines()
        self.generated_coupon_ids.write({'state': 'new'})
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        self.generated_coupon_ids.write({'state': 'expired'})
        self.applied_coupon_ids.write({'state': 'new'})
        return res

    def _get_reward_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda line: line.is_reward_line)

    def _is_reward_in_order_lines(self, program):
        self.ensure_one()
        return self.order_line.filtered(lambda line:
            line.product_id == program.reward_product_id and
            line.product_uom_qty >= program.reward_product_quantity)

    def _is_global_discount_already_applied(self):
        applied_programs = self.no_code_promo_program_ids + \
                           self.code_promo_program_id + \
                           self.applied_coupon_ids.mapped('program_id')
        return applied_programs.filtered(lambda program: program._is_global_discount_program())

    def _get_reward_values_product(self, program):
        price_unit = self.order_line.filtered(lambda line: program.reward_product_id == line.product_id)[0].price_unit

        order_lines = (self.order_line - self._get_reward_lines()).filtered(lambda x: program._is_valid_product(x.product_id))
        max_product_qty = sum(order_lines.mapped('product_uom_qty')) or 1
        # Remove needed quantity from reward quantity if same reward and rule product
        if program._is_valid_product(program.reward_product_id):
            reward_product_qty = max_product_qty // (program.rule_min_quantity + program.reward_product_quantity)
        else:
            reward_product_qty = max_product_qty

        reward_qty = min(int(int(max_product_qty / program.rule_min_quantity) * program.reward_product_quantity), reward_product_qty)
        # Take the default taxes on the reward product, mapped with the fiscal position
        taxes = program.reward_product_id.taxes_id
        if self.fiscal_position_id:
            taxes = self.fiscal_position_id.map_tax(taxes)
        return {
            'product_id': program.discount_line_product_id.id,
            'price_unit': - price_unit,
            'product_uom_qty': reward_qty,
            'is_reward_line': True,
            'name': "Free Product - " + program.reward_product_id.name,
            'product_uom': program.reward_product_id.uom_id.id,
            'tax_id': [(4, tax.id, False) for tax in taxes],
        }

    def _get_order_lines_untaxed_amount(self):
        """ Returns the untaxed sale order total amount without the rewards amount"""
        return sum([x.price_subtotal for x in self.order_line.filtered(lambda x: not x.is_reward_line)])

    def _get_reward_values_discount_fixed_amount(self, program):
        total_amount = sum(self.order_line.filtered(lambda line: not line.is_reward_line).mapped('price_total'))
        fixed_amount = program._compute_program_amount('discount_fixed_amount', self.currency_id)
        if total_amount < fixed_amount:
            return total_amount
        else:
            return fixed_amount

    def _get_lines_unit_prices(self):
        return [x.price_unit for x in self.order_line.filtered(lambda x: not x.is_reward_line)]

    def _get_reward_values_discount_percentage(self, program):
        discount_amount = 0
        amount_untaxed = self._get_order_lines_untaxed_amount()
        max_amount = program._compute_program_amount('discount_max_amount', self.currency_id)
        if program.discount_apply_on == 'on_order':
            discount_amount = amount_untaxed * (program.discount_percentage / 100)
        if program.discount_apply_on == 'cheapest_product':
            unit_prices = self._get_lines_unit_prices()
            discount_amount = (min(unit_prices) * (program.discount_percentage) / 100)
        if program.discount_apply_on == 'specific_product':
            discount_amount = sum([(x.price_unit * x.product_uom_qty) * (program.discount_percentage / 100) for x in self.order_line.filtered(
                lambda x: x.product_id == program.discount_specific_product_id)])
        if program.discount_max_amount and discount_amount > max_amount:
            discount_amount = max_amount
        return discount_amount

    def _get_reward_values_discount(self, program):
        if program.discount_type == 'percentage':
            discount_amount = self._get_reward_values_discount_percentage(program)
        elif program.discount_type == 'fixed_amount':
            discount_amount = self._get_reward_values_discount_fixed_amount(program)
        return {
            'name': "Discount: %s" % (program.name),
            'product_id': program.discount_line_product_id.id,
            'price_unit': - discount_amount,
            'product_uom_qty': 1.0,
            'product_uom': program.discount_line_product_id.uom_id.id,
            'is_reward_line': True
        }

    def _get_reward_line_values(self, program):
        self.ensure_one()
        if program.reward_type == 'discount':
            return self._get_reward_values_discount(program)
        elif program.reward_type == 'product':
            return self._get_reward_values_product(program)

    def _create_reward_line(self, programs):
        self.ensure_one()
        for program in programs:
            self.write({'order_line': [(0, False, self._get_reward_line_values(program))]})

    def _create_reward_coupon(self, program):
        coupon = self.env['sale.coupon'].create({
            'program_id': program.id,
            'state': 'reserved',
            'partner_id': self.partner_id.id,
            'order_id': self.id,
            'discount_line_product_id': program.discount_line_product_id.id
        })
        self.generated_coupon_ids |= coupon
        subject = '%s, a coupon has been generated from your order %s' % (self.partner_id.name, self.name)
        body = self.env.ref('sale_coupon.sale_coupon_created_coupon_email_template').render({
            'code': coupon.code,
            'reward_description': coupon.program_id.discount_line_product_id.name
            })
        self.message_post(body=body, subject=subject, subtype='mail.mt_comment', partner_ids=[(4, self.partner_id.id)])
        return coupon

    def _get_applicable_programs(self):
        """
        This method is used to return the valid applicable programs on given order.
        param: order - The sale order for which method will get applicable programs.
        """
        self.ensure_one()
        programs = self.env['sale.coupon.program'].search([
            ('active', '=', True)
        ])._filter_programs_from_common_rules(self)
        if self.promo_code:
            programs._filter_promo_programs_with_code(self)
        return programs

    def _get_applicable_no_code_promo_program(self):
        self.ensure_one()
        programs = self.env['sale.coupon.program'].search([
            ('active', '=', True),
            ('promo_code_usage', '=', 'no_code_needed'),
            # ('promo_applicability', '=', 'on_current_order')
        ])._filter_programs_from_common_rules(self)
        return programs.sorted('sequence')

    def _create_new_no_code_promo_reward_lines(self):
        '''Apply new programs that are applicable'''
        self.ensure_one()
        order = self
        programs = order._get_applicable_no_code_promo_program()
        for program in programs:
            error_status = program._check_promo_code(order, False)
            if not error_status.get('error') and program.promo_applicability == 'on_next_order':
                order._create_reward_coupon(program)
                order.no_code_promo_program_ids |= program
            elif not error_status.get('error') and program.discount_line_product_id.id not in self.order_line.mapped('product_id').ids:
                self.write({'order_line': [(0, False, order._get_reward_line_values(program))]})
                order.no_code_promo_program_ids |= program

    def _update_existing_reward_lines(self):
        '''Update values for already applied rewards'''
        self.ensure_one()
        order = self
        applied_programs = order.no_code_promo_program_ids + \
                           order.applied_coupon_ids.mapped('program_id') + \
                           order.code_promo_program_id
        for program in applied_programs:
            values = order._get_reward_line_values(program)
            lines = order.order_line.filtered(lambda line: line.product_id == program.discount_line_product_id)
            # Remove reward line if price or qty equal to 0
            if values['product_uom_qty'] and values['price_unit']:
                order.write({'order_line': [(1, line.id, values) for line in lines]})
            else:
                if program.reward_type != 'free_shipping':
                    order.write({'order_line': [(2, line.id, False) for line in lines]})
                else:
                    values.update(price_unit=0.0)
                    order.write({'order_line': [(1, line.id, values) for line in lines]})

    def _remove_invalid_reward_lines(self):
        '''Unlink reward order lines that are not applicable anymore'''
        invalid_lines = self.env['sale.order.line']
        for order in self:
            new_applicable_programs = order._get_applicable_no_code_promo_program() + order._get_applicable_programs()
            old_applicable_programs = order.no_code_promo_program_ids + order.applied_coupon_ids.mapped('program_id') + order.code_promo_program_id
            programs_to_remove = old_applicable_programs - new_applicable_programs
            products_to_remove = (programs_to_remove).mapped('discount_line_product_id')
            self.generated_coupon_ids.filtered(lambda coupon: coupon.program_id.discount_line_product_id.id in products_to_remove.ids).write({'state': 'expired'})
            order.no_code_promo_program_ids -= programs_to_remove
            order.code_promo_program_id -= programs_to_remove
            order.applied_coupon_ids -= order.applied_coupon_ids.filtered(lambda coupon: coupon.program_id in programs_to_remove)
            invalid_lines |= order.order_line.filtered(lambda line: line.product_id.id in products_to_remove.ids)
            order.write({'order_line': [(2, line.id, False) for line in invalid_lines]})

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_reward_line = fields.Boolean('Is a program reward line')

    def unlink(self):
        # Reactivate coupons related to unlinked reward line
        for line in self.filtered(lambda line: line.is_reward_line):
            coupons_to_reactivate = line.order_id.applied_coupon_ids.filtered(
                lambda coupon: coupon.program_id.discount_line_product_id == line.product_id
            )
            coupons_to_reactivate.write({'state': 'new'})
            line.order_id.applied_coupon_ids -= coupons_to_reactivate
        # Remove the program from the order in the case it's still valid
        for line in self:
            related_program = self.env['sale.coupon.program'].search([('discount_line_product_id', '=', line.product_id.id)])
            if related_program:
                line.order_id.no_code_promo_program_ids -= related_program
                line.order_id.code_promo_program_id -= related_program
        return super(SaleOrderLine, self).unlink()
