# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import ast


class CouponProgram(models.Model):
    _name = 'coupon.program'
    _description = "Coupon Program"
    _inherits = {'coupon.rule': 'rule_id', 'coupon.reward': 'reward_id'}
    # We should apply 'discount' promotion first to avoid offering free product when we should not.
    # Eg: If the discount lower the SO total below the required threshold
    # Note: This is only revelant when programs have the same sequence (which they have by default)
    _order = "sequence, reward_type"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean('Active', default=True, help="A program is available for the customers when active")
    rule_id = fields.Many2one('coupon.rule', string="Coupon Rule", ondelete='restrict', required=True)
    reward_id = fields.Many2one('coupon.reward', string="Reward", ondelete='restrict', required=True, copy=False)
    sequence = fields.Integer(copy=False,
        help="Coupon program will be applied based on given sequence if multiple programs are " +
        "defined on same condition(For minimum amount)")
    maximum_use_number = fields.Integer(help="Maximum number of sales orders in which reward can be provided")
    program_type = fields.Selection([
        ('promotion_program', 'Promotional Program'),
        ('coupon_program', 'Coupon Program'),
        ],
        help="""A promotional program can be either a limited promotional offer without code (applied automatically)
                or with a code (displayed on a magazine for example) that may generate a discount on the current
                order or create a coupon for a next order.

                A coupon program generates coupons with a code that can be used to generate a discount on the current
                order or create a coupon for a next order.""")
    promo_code_usage = fields.Selection([
        ('no_code_needed', 'Automatically Applied'),
        ('code_needed', 'Use a code')],
        help="Automatically Applied - No code is required, if the program rules are met, the reward is applied (Except the global discount or the free shipping rewards which are not cumulative)\n" +
             "Use a code - If the program rules are met, a valid code is mandatory for the reward to be applied\n")
    promo_code = fields.Char('Promotion Code', copy=False,
        help="A promotion code is a code that is associated with a marketing discount. For example, a retailer might tell frequent customers to enter the promotion code 'THX001' to receive a 10%% discount on their whole order.")
    promo_applicability = fields.Selection([
        ('on_current_order', 'Apply On Current Order'),
        ('on_next_order', 'Send a Coupon')],
        default='on_current_order', string="Applicability")
    coupon_ids = fields.One2many('coupon.coupon', 'program_id', string="Generated Coupons", copy=False)
    coupon_count = fields.Integer(compute='_compute_coupon_count')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    validity_duration = fields.Integer(default=30,
        help="Validity duration for a coupon after its generation")

    @api.constrains('promo_code')
    def _check_promo_code_constraint(self):
        """ Program code must be unique """
        for program in self.filtered(lambda p: p.promo_code):
            domain = [('id', '!=', program.id), ('promo_code', '=', program.promo_code)]
            if self.search(domain):
                raise ValidationError(_('The program code must be unique!'))

    @api.depends('coupon_ids')
    def _compute_coupon_count(self):
        coupon_data = self.env['coupon.coupon'].read_group([('program_id', 'in', self.ids)], ['program_id'], ['program_id'])
        mapped_data = dict([(m['program_id'][0], m['program_id_count']) for m in coupon_data])
        for program in self:
            program.coupon_count = mapped_data.get(program.id, 0)

    @api.onchange('promo_code_usage')
    def _onchange_promo_code_usage(self):
        if self.promo_code_usage == 'no_code_needed':
            self.promo_code = False

    @api.onchange('reward_product_id')
    def _onchange_reward_product_id(self):
        if self.reward_product_id:
            self.reward_product_uom_id = self.reward_product_id.uom_id

    @api.onchange('discount_type')
    def _onchange_discount_type(self):
        if self.discount_type == 'fixed_amount':
            self.discount_apply_on = 'on_order'

    @api.model
    def create(self, vals):
        program = super(CouponProgram, self).create(vals)
        if not vals.get('discount_line_product_id', False):
            values = program._get_discount_product_values()
            discount_line_product_id = self.env['product.product'].create(values)
            program.write({'discount_line_product_id': discount_line_product_id.id})
        return program

    def write(self, vals):
        res = super(CouponProgram, self).write(vals)
        reward_fields = [
            'reward_type', 'reward_product_id', 'discount_type', 'discount_percentage',
            'discount_apply_on', 'discount_specific_product_ids', 'discount_fixed_amount'
        ]
        if any(field in reward_fields for field in vals):
            self.mapped('discount_line_product_id').write({'name': self[0].reward_id.display_name})
        return res

    def unlink(self):
        if self.filtered('active'):
            raise UserError(_('You can not delete a program in active state'))
        # get reference to rule and reward
        rule = self.rule_id
        reward = self.reward_id
        # unlink the program
        super(CouponProgram, self).unlink()
        # then unlink the rule and reward
        rule.unlink()
        reward.unlink()
        return True

    def toggle_active(self):
        super(CouponProgram, self).toggle_active()
        for program in self:
            program.discount_line_product_id.active = program.active
        coupons = self.filtered(lambda p: not p.active and p.promo_code_usage == 'code_needed').mapped('coupon_ids')
        coupons.filtered(lambda x: x.state != 'used').write({'state': 'expired'})

    def _compute_program_amount(self, field, currency_to):
        self.ensure_one()
        return self.currency_id._convert(self[field], currency_to, self.company_id, fields.Date.today())

    def _is_valid_partner(self, partner):
        if self.rule_partners_domain and self.rule_partners_domain != '[]':
            domain = ast.literal_eval(self.rule_partners_domain) + [('id', '=', partner.id)]
            return bool(self.env['res.partner'].search_count(domain))
        else:
            return True

    def _is_valid_product(self, product):
        # NOTE: if you override this method, think of also overriding _get_valid_products
        # we also encourage the use of _get_valid_products as its execution is faster
        if self.rule_products_domain:
            domain = ast.literal_eval(self.rule_products_domain) + [('id', '=', product.id)]
            return bool(self.env['product.product'].search_count(domain))
        else:
            return True

    def _get_valid_products(self, products):
        if self.rule_products_domain:
            domain = ast.literal_eval(self.rule_products_domain)
            return products.filtered_domain(domain)
        return products

    def _get_discount_product_values(self):
        return {
            'name': self.reward_id.display_name,
            'type': 'service',
            'taxes_id': False,
            'supplier_taxes_id': False,
            'sale_ok': False,
            'purchase_ok': False,
            'lst_price': 0, #Do not set a high value to avoid issue with coupon code
        }
