# -*- coding: utf-8 -*-

import math
from openerp import models, fields, api, _
from openerp.exceptions import MissingError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    #reward_coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")
    coupon_program_ids = fields.One2many('sale.couponprogram', 'sale_order_id', string='Coupon Programs')
    applied_coupon_ids = fields.One2many('sale.coupon', 'used_in_order_id', string="Applied Coupons")
    #generated_coupon_ids = fields.One2many('sale.coupon', 'origin_order_id', string="Generated coupons")

    @api.multi
    def _merge_duplicate_product_line(self):
        product_line = []
        line_to_remove = []
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward')
        for line in self.order_line.filtered(lambda x: x.product_id != reward_product_id):
            product_line = self.order_line.filtered(lambda x: x.product_id == line.product_id and x.id != line.id)
            for p_line in product_line:
                if p_line and (line not in line_to_remove):
                    line.with_context(nocoupon=True).write({'product_uom_qty': line.product_uom_qty + p_line.product_uom_qty})
                    line_to_remove += p_line
        for remove_line in line_to_remove:
            remove_line.unlink()

    def _prepare_domain(self, domain, amount, amount_untaxed, partner_id):
        return domain + [
            '&', ('purchase_type', '=', 'amount'), '|',
            '&', ('reward_tax', '=', 'tax_excluded'), ('minimum_amount', '<=', amount),
            '&', ('reward_tax', '=', 'tax_included'), ('minimum_amount', '<=', amount_untaxed),
            '|', ('partner_id', '=', None), ('partner_id', '=', partner_id.id)]

    def _search_reward_programs(self, domain=[]):
        program = self.env['sale.couponprogram'].search(self._prepare_domain(domain, self.amount_total, self.amount_untaxed, self.partner_id),
                                                        limit=1, order='program_sequence')
        if not program:
            reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id.id is False and x.product_id == self.env.ref('website_sale_coupon.product_product_reward'))
            if reward_line:
                domain += [('reward_discount_on', '!=', 'cheapest_product'), ('reward_discount_on', '!=', 'specific_product'), ('reward_type', '=', 'discount')]
                program = self.env['sale.couponprogram'].search(self._prepare_domain(domain, self.amount_total - reward_line.price_unit, self.amount_untaxed - reward_line.price_unit, self.partner_id),
                                                                limit=1, order='program_sequence')
        if program:
            return program

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        res = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty)
        self.apply_immediately_reward()
        return res

    def _check_current_reward_applicability(self, domain=[], program_type=False):
        remove_reward_lines = []
        for order in self.filtered(lambda x: x.order_line is not False):
            order_reward_lines = self._check_reward_on_order(order, domain, program_type)
            if order_reward_lines:
                remove_reward_lines += order_reward_lines
            reward_lines = self._check_reward_on_lines(order, domain, program_type)
            if reward_lines:
                remove_reward_lines += reward_lines
        for remove_line in remove_reward_lines:
            remove_line.with_context(nocoupon=True).unlink()

    def _check_reward_on_order(self, order, domain, program_type):
        remove_reward_lines = []
        reward_lines = order.order_line.filtered(lambda x: x.coupon_program_id.purchase_type == 'amount' and x.coupon_program_id.program_type == program_type)
        for reward_line in reward_lines:
            program = reward_line.coupon_program_id
            #check for customer
            if program.partner_id.id is not False and program.partner_id != self.partner_id:
                remove_reward_lines += reward_line
            #check discount amount if discount is on cart
            if (program.reward_discount_on == 'cart' and
               program.reward_discount_type == 'percentage' and
               program.reward_type == 'discount') or program.reward_discount_on == 'cheapest_product':
                if program.applicability_tax == 'tax_excluded':
                    amount = order.amount_total
                if program.applicability_tax == 'tax_included':
                    amount = order.amount_untaxed
                discount_amount = amount + ((-1) * reward_line.price_unit)
                if discount_amount < program.minimum_amount:
                    remove_reward_lines += reward_line
            else:
                #check for total amt
                if self.amount_total < program.minimum_amount:
                    remove_reward_lines += reward_line
        return remove_reward_lines

    def _check_reward_on_lines(self, order, domain, program_type):
        remove_reward_lines = []
        for order_line in [x for x in order.order_line if not (x.coupon_program_id or x.generated_from_line_id)]:
            programs = order_line._search_reward_programs(domain)
            if programs:
                reward_lines = self._check_delivery_charge_line(programs)
                if reward_lines:
                    remove_reward_lines += reward_lines
                reward_lines = self._check_reward_product_line(order_line, programs)
                if reward_lines:
                    remove_reward_lines += reward_lines
            else:
                remove_reward_lines += self.order_line.filtered(lambda x: x.generated_from_line_id == order_line and x.coupon_program_id.id is not False and program_type and x.coupon_program_id.program_type == program_type)
        return remove_reward_lines

    def _check_reward_product_line(self, order_line, programs):
        reward_line = []
        remove_reward_lines = []
        for program in programs.filtered(lambda x: x.reward_type == 'product' or (x.reward_type == 'discount' and x.reward_discount_on == 'specific_product')):
            product_line = self.order_line.filtered(lambda x: x.product_id == program.reward_product_product_id or x.product_id == program.reward_discount_on_product_id)
            if not product_line:
                reward_line = self.order_line.filtered(lambda x: x.coupon_program_id == program and x.generated_from_line_id == order_line)
                remove_reward_lines += reward_line
        return remove_reward_lines

    def _check_delivery_charge_line(self, programs):
        reward_line = []
        remove_reward_lines = []
        for program in programs.filtered(lambda x: x.reward_type == 'free_shipping'):
            reward_line = self.order_line.filtered(lambda x: x.coupon_program_id == program)
            delivery_charge_line = self.order_line.filtered(lambda x: x.product_id.is_delivery_charge_product)
            if reward_line and not delivery_charge_line:
                remove_reward_lines += reward_line
        return remove_reward_lines

    def _process_reward_product(self, program, coupon_code):
        product_lines = self.order_line.filtered(lambda x: x.product_id == program.reward_product_product_id)
        vals = self.order_line.product_id_change(self.pricelist_id.id, program.reward_product_product_id.id, program.reward_quantity
                                                 )['value']
        if not product_lines:
            vals['product_id'] = program.reward_product_product_id.id
            vals['product_uom_qty'] = program.reward_quantity
            vals['order_id'] = self.id
            vals['coupon_id'] = coupon_code
            line = self.order_line.with_context(noreward=True).create(vals)
        else:
            line = product_lines[0]
            if line.product_uom_qty < program.reward_quantity:
                line.with_context(noreward=True).write({'product_uom_qty': program.reward_quantity})
        self._create_discount_reward(program, vals['price_unit'], coupon_code)

    def _process_reward_discount(self, program, coupon_code):
        if program.reward_discount_type == 'amount':
            discount_amount = program.reward_discount_amount
        elif program.reward_discount_type == 'percentage':
            if program.reward_discount_on == 'cart':
                reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id.id is False and x.coupon_program_id == program)
                if reward_line:
                    discount_amount = ((self.amount_total - (reward_line.price_unit)) * (program.reward_discount_percentage / 100))
                else:
                    discount_amount = self.amount_total * (program.reward_discount_percentage / 100)
            elif program.reward_discount_on == 'cheapest_product':
                    unit_prices = [x.price_unit for x in self.order_line if x.coupon_program_id.id is False]
                    discount_amount = (min(unit_prices) * (program.reward_discount_percentage) / 100)
            elif program.reward_discount_on == 'specific_product':
                discount_amount = sum([x.price_unit * (program.reward_discount_percentage / 100) for x in self.order_line if x.product_id == program.reward_discount_on_product_id])
        self._create_discount_reward(program, discount_amount, coupon_code)

    def _process_reward_coupon(self, program, coupon_code):
        pass
        #self.coupon_program_id = program.reward_gift_program_id.id
        #self.reward_program_ids = program.id

    def _process_reward_free_shipping(self, program, coupon_code):
        delivery_charge_line = self.order_line.filtered(lambda x: x.product_id.is_delivery_charge_product)
        if delivery_charge_line:
            vals = {
                'product_id': self.env.ref('website_sale_coupon.product_product_reward').id,
                'name': _("Free Shipping"),
                'product_uom_qty': 1,
                'price_unit': -delivery_charge_line.price_unit,
                'order_id': self.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': False,
                'coupon_id': coupon_code
            }
            self.order_line.with_context(noreward=True).create(vals)
            program.sale_order_id = self.id

    def _create_discount_reward(self, program, discount_amount, coupon_code):
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward')
        reward_lines = self.order_line.filtered(lambda x: x.generated_from_line_id.id is False and x.product_id.id == reward_product_id.id and x.coupon_program_id == program)
        if discount_amount <= 0 and reward_lines:
            reward_lines.unlink()
        elif discount_amount > 0 and reward_lines:
            reward_lines.with_context(noreward=True).write({'price_unit': -discount_amount})
        elif discount_amount > 0 and not reward_lines:
            desc = program.get_reward_string()
            vals = {
                'product_id': reward_product_id.id,
                'name': desc,
                'product_uom_qty': program.reward_quantity,
                'price_unit': -discount_amount,
                'order_id': self.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': False,
                'coupon_id': coupon_code
            }
            self.order_line.with_context(noreward=True).create(vals)
            program.sale_order_id = self.id
            if coupon_code:
                coupon_obj = self.env['sale.coupon'].search([('coupon_code', '=', coupon_code)])
                if coupon_obj:
                    coupon_obj.state = 'used'
                    coupon_obj.used_in_order_id = self.id
                    coupon_obj.nbr_used = coupon_obj.nbr_used + 1
                    coupon_obj.reward_name = desc

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res._merge_duplicate_product_line()
        if vals.get('order_line'):
            res.apply_immediately_reward()
        return res

    @api.multi
    def write(self, vals):
        if not self.is_reward_line_updated(vals):
            res = super(SaleOrder, self).write(vals)
            self._merge_duplicate_product_line()
            if vals.get('order_line'):
                self.apply_immediately_reward()
            return res
        return True

    def is_reward_line_updated(self, vals):
        if vals.get('order_line'):
            for order_line in vals.get('order_line'):
                if order_line[2] is not False and self.order_line.browse(order_line[1]).product_id == self.env.ref('website_sale_coupon.product_product_reward'):
                    return True

    def check_reward_type_discount_on_cart(self, program):
        if program.reward_discount_type == 'percentage' and \
           program.reward_type == 'discount' and \
           program.reward_discount_on == 'cart':
                reward_line = self.order_line.filtered(lambda x: x.product_id == self.env.ref('website_sale_coupon.product_product_reward') and x.coupon_program_id != program)
                if reward_line.coupon_program_id.reward_discount_type == 'percentage' and \
                   reward_line.coupon_program_id.reward_type == 'discount' and \
                   reward_line.coupon_program_id.reward_discount_on == 'cart':
                        return True
                else:
                    return False

    @api.multi
    def apply_immediately_reward(self):
        for order in self.filtered(lambda x: x.order_line is not False):
            programs = order._search_reward_programs([('program_type', '=', 'apply_immediately'), ('state', '=', 'opened')])
            if programs:
                    self.process_rewards(programs, False)
            for order_line in [x for x in order.order_line if not (x.coupon_program_id or x.generated_from_line_id)]:
                order_line.apply_immediately_reward()
            self._check_current_reward_applicability([('program_type', '=', 'apply_immediately'), ('state', '=', 'opened')], 'apply_immediately')
            self._check_current_reward_applicability([('program_type', '=', 'public_unique_code'), ('state', '=', 'opened')], 'public_unique_code')
            self._check_current_reward_applicability([('program_type', '=', 'generated_coupon'), ('state', '=', 'opened')], 'generated_coupon')

    @api.multi
    def apply_coupon_reward(self, coupon_code):
        program = self.env['sale.couponprogram'].search([('program_code', '=', coupon_code), ('state', '=', 'opened')], limit=1)
        if not program:
            coupon_obj = self.env['sale.coupon'].search([('coupon_code', '=', coupon_code), ('program_id.state', '=', 'opened')], limit=1)
            if not coupon_obj:
                return {'error': _('Coupon %s is invalid.') % (coupon_code)}
            if coupon_obj.state == 'used':
                return {'error': _('Coupon %s has been used.') % (coupon_code)}
            program = coupon_obj.program_id
        if program.check_is_program_expired(coupon_code):
            return {'error': _('Code %s has been expired') % (coupon_code)}
        if program.state == 'closed':
            return {'error': _('Program has been closed')}
        if program.program_type != 'apply_immediately':
            if program.purchase_type == 'amount' and ((self.amount_total >= program.minimum_amount and program.reward_tax == 'tax_excluded') or
                                                     (self.amount_untaxed >= program.minimum_amount and program.reward_tax == 'tax_excluded')):
                reward_product_id = self.env.ref('website_sale_coupon.product_product_reward')
                reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id.id is False and x.product_id == reward_product_id)
                if reward_line:
                    return {'error': _('Code %s is already applied') % (coupon_code)}
                else:
                    self.process_rewards(program, coupon_code)
            if program.purchase_type == 'product':
                for line in self.order_line.filtered(lambda x: x.product_id == program.product_id and x.product_uom_qty >= program.product_quantity):
                    reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id == line)
                    if reward_line:
                        return {'error': _('Code %s is already applied') % (coupon_code)}
                    else:
                        line.process_rewards(program, coupon_code)
            if program.purchase_type == 'category':
                for line in self.order_line.filtered(lambda x: x.product_id.categ_id == program.product_category_id and x.product_uom_qty >= program.product_quantity):
                    reward_line = self.order_line.filtered(lambda x: x.generated_from_line_id == line)
                    if reward_line:
                        return {'error': _('Code %s is already applied') % (coupon_code)}
                    else:
                        line.process_rewards(program, coupon_code)
            #self._check_for_free_shipping(coupon_code)
        return {'update_price': True}

    @api.multi
    def process_rewards(self, programs, coupon_code):
        for program in programs:
            if not self.check_reward_type_discount_on_cart(program):
                getattr(self, '_process_reward_' + program.reward_type)(program, coupon_code)

    @api.multi
    def open_apply_coupon_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Enter coupon code",
            'res_model': 'sale.get.coupon',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    coupon_id = fields.Char(string="Coupon")
    coupon_program_id = fields.Many2one('sale.couponprogram', string="Coupon program")
    generated_from_line_id = fields.Many2one('sale.order.line')

    def _search_reward_programs(self, domain=[]):
        return self.env['sale.couponprogram'].search(domain + [
            '&', ('product_quantity', '<=', self.product_uom_qty),
            '|',
            '&', ('purchase_type', '=', 'product'), ('product_id', '=', self.product_id.id),
            '&', ('purchase_type', '=', 'category'), ('product_category_id', '=', self.product_id.categ_id.id),
            '|', ('partner_id', '=', None), ('partner_id', '=', self.order_id.partner_id.id)], order='program_sequence')

    def _create_discount_reward(self, program, qty, discount_amount, coupon_code):
        reward_product_id = self.env.ref('website_sale_coupon.product_product_reward').id
        reward_lines = self.order_id.order_line.filtered(lambda x: x.generated_from_line_id == self and x.product_id.id == reward_product_id and x.coupon_program_id == program)
        if discount_amount <= 0 and reward_lines:
            reward_lines.unlink()
        elif discount_amount > 0 and reward_lines:
            for reward_line in reward_lines:
                reward_line.with_context(noreward=True).write({'price_unit': -discount_amount, 'product_uom_qty': qty})
        if discount_amount > 0 and not reward_lines:
            desc = program.get_reward_string()
            vals = {
                'product_id': reward_product_id,
                'name': desc,
                'product_uom_qty': qty,
                'price_unit': -discount_amount,
                'order_id': self.order_id.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': self.id,
                'coupon_id': coupon_code
            }
            self.with_context(noreward=True).create(vals)
            program.sale_order_id = self.order_id.id
            if coupon_code:
                coupon_obj = self.env['sale.coupon'].search([('coupon_code', '=', coupon_code)])
                if coupon_obj:
                    coupon_obj.state = 'used'
                    coupon_obj.used_in_order_id = self.order_id.id
                    coupon_obj.nbr_used = coupon_obj.nbr_used + 1
                    coupon_obj.reward_name = desc

    def _process_reward_product(self, program, coupon_code):
        product_lines = self.order_id.order_line.filtered(lambda x: x.product_id == program.reward_product_product_id)
        vals = self.product_id_change(self.order_id.pricelist_id.id, program.reward_product_product_id.id, program.reward_quantity
                                      )['value']
        if product_lines:
            line = product_lines[0]
        if program.reward_product_product_id == program.product_id:
            to_reward_qty = math.floor(self.product_uom_qty / (program.product_quantity + program.reward_quantity))
            if not (to_reward_qty) and (line.product_uom_qty == program.product_quantity):
                product_qty = line.product_uom_qty + program.reward_quantity
                line.with_context(nocoupon=True).write({'product_uom_qty': product_qty})
                to_reward_qty = 1
        else:
            to_reward_qty = math.floor(self.product_uom_qty / program.product_quantity * program.reward_quantity)
        if not to_reward_qty:
            vals['price_unit'] = 0
        if not product_lines:
            vals['product_id'] = program.reward_product_product_id.id
            vals['product_uom_qty'] = to_reward_qty
            vals['order_id'] = self.order_id.id
            vals['coupon_id'] = coupon_code
            line = self.with_context(noreward=True).create(vals)
        else:
            if program.reward_product_product_id.id == line.product_id.id and \
               program.reward_product_product_id != program.product_id and line.product_uom_qty <= to_reward_qty:
                    line.with_context(noreward=True).write({'product_uom_qty': to_reward_qty})
        self._create_discount_reward(program, to_reward_qty, vals['price_unit'], coupon_code)

    def _process_reward_discount(self, program, coupon_code):
        discount_amount = 0
        if program.reward_discount_type == 'amount':
            discount_amount = program.reward_discount_amount
        elif program.reward_discount_type == 'percentage':
            if program.reward_discount_on == 'cart':
                discount_amount = self.order_id.amount_total * (program.reward_discount_percentage / 100)
            elif program.reward_discount_on == 'cheapest_product':
                    unit_prices = [x.price_unit for x in self.order_id.order_line if x.coupon_program_id.id is False]
                    discount_amount = (min(unit_prices) * (program.reward_discount_percentage) / 100)
            elif program.reward_discount_on == 'specific_product':
                discount_amount = sum([x.price_unit * (program.reward_discount_percentage / 100) for x in self.order_id.order_line if x.product_id == program.reward_discount_on_product_id])
        self._create_discount_reward(program, 1, discount_amount, coupon_code)

        def _process_reward_coupon(self, program, coupon_code):
            pass
            #self.order_id.coupon_program_id = program.reward_gift_program_id.id
            #self.order_id.reward_program_ids = program.id

    def _process_reward_free_shipping(self, program, coupon_code):
        delivery_charge_line = self.order_id.order_line.filtered(lambda x: x.product_id.is_delivery_charge_product)
        reward_line = self.order_id.order_line.filtered(lambda x: x.coupon_program_id == program and x.generated_from_line_id == self)
        if delivery_charge_line and not reward_line:
            vals = {
                'product_id': self.env.ref('website_sale_coupon.product_product_reward').id,
                'name': _("Free Shipping"),
                'product_uom_qty': 1,
                'price_unit': -delivery_charge_line.price_unit,
                'order_id': self.order_id.id,
                'coupon_program_id': program.id,
                'generated_from_line_id': self.id,
                'coupon_id': coupon_code
            }
            self.with_context(noreward=True).create(vals)
            program.sale_order_id = self.order_id.id

    @api.multi
    def unlink(self):
        res = True
        try:
            reward_lines = self.filtered(lambda x: x.coupon_program_id.id is not False)
            for line in reward_lines:
                # if line.generated_from_line_id.product_id != self.env.ref('website_sale_coupon.product_product_reward'):
                if line.coupon_program_id.sale_order_id.filtered(lambda x: x == self.order_id):
                    line.coupon_program_id.sale_order_id = False
            reward_lines = self.filtered(lambda x: x.coupon_id is not False)
            for line in reward_lines:
                coupon_obj = self.env['sale.coupon'].search([('coupon_code', '=', line.coupon_id)])
                if coupon_obj:
                    coupon_obj.state = 'new'
                    coupon_obj.reward_name = ""
                    coupon_obj.used_in_order_id = False
                    if coupon_obj.nbr_used > 1:
                        coupon_obj.nbr_used -= 1
                    else:
                        coupon_obj.nbr_used = 0
            reward_lines = self.order_id.order_line.filtered(lambda x: x.generated_from_line_id.id in self.ids)
            for line_obj in self:
                line = self.order_id.order_line.filtered(lambda x: x.generated_from_line_id.id is False and (x.coupon_program_id.reward_product_product_id == line_obj.product_id or x.coupon_program_id.reward_discount_on_product_id == line_obj.product_id))
                if line:
                    reward_lines += line
            if reward_lines:
                for reward_line in reward_lines:
                    reward_line.unlink()
            res = super(SaleOrderLine, self).unlink()
        except MissingError:
            pass
        return res

    @api.multi
    def process_rewards(self, programs, coupon_code):
        for program in programs:
            if not self.order_id.check_reward_type_discount_on_cart(program):
                getattr(self, '_process_reward_' + program.reward_type)(program, coupon_code)

    @api.multi
    def apply_immediately_reward(self):
        programs = self._search_reward_programs([('program_type', '=', 'apply_immediately'), ('state', '=', 'opened')])
        if programs:
            self.process_rewards(programs, False)
        return programs

    # @api.multi
    # def button_confirm(self):
    #     res = super(SaleOrderLine, self).button_confirm()
    #     line = self[0]
    #     if line.order_id.coupon_program_id:
    #         coupon_obj = self.env['sale.coupon']
    #         for coupon_program in self.order_id.coupon_program_id:
    #             coupon_obj.create({'program_id': coupon_program.id, 'nbr_uses': 1, 'origin_order_id': line.order_id.id})
    #     return res
