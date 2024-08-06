# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class SaleCouponApplyCode(models.TransientModel):
    _name = 'sale.coupon.apply.code'
    _rec_name = 'coupon_code'
    _description = 'Sales Coupon Apply Code'

    coupon_code = fields.Char(string="Code", required=True)

    def process_coupon(self):
        """
        Apply the entered coupon code if valid, raise an UserError otherwise.
        """
        sales_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        error_status = self.apply_coupon(sales_order, self.coupon_code)
        if error_status.get('error', False):
            raise UserError(error_status.get('error', False))
        if error_status.get('not_found', False):
            raise UserError(error_status.get('not_found', False))

    def apply_coupon(self, order, coupon_code):
        error_status = {}
        program_domain = order._get_coupon_program_domain()
        program_domain = expression.AND([program_domain, [('promo_code', '=', coupon_code)]])
        program = self.env['coupon.program'].search(program_domain)
        if program:
            error_status = program._check_promo_code(order, coupon_code)
            if not error_status:
                if program.promo_applicability == 'on_next_order':
                    # Avoid creating the coupon if it already exist
                    if program.discount_line_product_id.id not in order.generated_coupon_ids.filtered(lambda coupon: coupon.state in ['new', 'reserved']).mapped('discount_line_product_id').ids:
                        coupon = order._create_reward_coupon(program)
                        return {
                            'generated_coupon': {
                                'reward': coupon.program_id.discount_line_product_id.name,
                                'code': coupon.code,
                            }
                        }
                else:  # The program is applied on this order
                    # Only link the promo program if reward lines were created
                    order_line_count = len(order.order_line)
                    order._create_reward_line(program)
                    if order_line_count < len(order.order_line):
                        order.code_promo_program_id = program
        else:
            coupon = self.env['coupon.coupon'].search([('code', '=', coupon_code)], limit=1)
            if coupon:
                error_status = coupon._check_coupon_code(order)
                if not error_status:
                    # Consume coupon only if reward lines were created
                    order_line_count = len(order.order_line)
                    order._create_reward_line(coupon.program_id)
                    if order_line_count < len(order.order_line):
                        order.applied_coupon_ids += coupon
                        coupon.write({'state': 'used'})
            else:
                error_status = {'not_found': _('This coupon is invalid (%s).') % (coupon_code)}
        return error_status
