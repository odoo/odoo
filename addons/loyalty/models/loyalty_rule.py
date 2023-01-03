# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _description = 'Loyalty Rule'

    @api.model
    def default_get(self, fields_list):
        # Try to copy the values of the program types default's
        result = super().default_get(fields_list)
        if 'program_type' in self.env.context:
            program_type = self.env.context['program_type']
            program_default_values = self.env['loyalty.program']._program_type_default_values()
            if program_type in program_default_values and\
                len(program_default_values[program_type]['rule_ids']) == 2 and\
                isinstance(program_default_values[program_type]['rule_ids'][1][2], dict):
                result.update({
                    k: v for k, v in program_default_values[program_type]['rule_ids'][1][2].items() if k in fields_list
                })
        return result

    def _get_reward_point_mode_selection(self):
        # The value is provided in the loyalty program's view since we may not have a program_id yet
        #  and makes sure to display the currency related to the program instead of the company's.
        symbol = self.env.context.get('currency_symbol', self.env.company.currency_id.symbol)
        return [
            ('order', _('per order')),
            ('money', _('per %s spent', symbol)),
            ('unit', _('per unit paid')),
        ]

    active = fields.Boolean(default=True)
    program_id = fields.Many2one('loyalty.program', required=True, ondelete='cascade')
    program_type = fields.Selection(related="program_id.program_type")
    # Stored for security rules
    company_id = fields.Many2one(related='program_id.company_id', store=True)
    currency_id = fields.Many2one(related='program_id.currency_id')

    # Only for dev mode
    user_has_debug = fields.Boolean(compute='_compute_user_has_debug')
    product_domain = fields.Char(default="[]")

    product_ids = fields.Many2many('product.product', string='Products')
    product_category_id = fields.Many2one('product.category', string='Categories')
    product_tag_id = fields.Many2one('product.tag', string='Product Tag')

    reward_point_amount = fields.Float(default=1, string="Reward")
    # Only used for program_id.applies_on == 'future'
    reward_point_split = fields.Boolean(string='Split per unit', default=False,
        help="Whether to separate reward coupons per matched unit, only applies to 'future' programs and trigger mode per money spent or unit paid..")
    reward_point_name = fields.Char(related='program_id.portal_point_name', readonly=True)
    reward_point_mode = fields.Selection(selection=_get_reward_point_mode_selection, required=True, default='order')

    minimum_qty = fields.Integer('Minimum Quantity', default=1)
    minimum_amount = fields.Monetary('Minimum Purchase', 'currency_id')
    minimum_amount_tax_mode = fields.Selection([
        ('incl', 'Included'),
        ('excl', 'Excluded')], default='incl', required=True,
    )

    mode = fields.Selection([
        ('auto', 'Automatic'),
        ('with_code', 'With a promotion code'),
    ], string="Application", compute='_compute_mode', store=True, readonly=False)
    code = fields.Char(string='Discount code', compute='_compute_code', store=True, readonly=False)

    _sql_constraints = [
        ('reward_point_amount_positive', 'CHECK (reward_point_amount > 0)', 'Rule points reward must be strictly positive.'),
    ]

    @api.constrains('reward_point_split')
    def _constraint_trigger_multi(self):
        # Prevent setting trigger multi in case of nominative programs, it does not make sense to allow this
        for rule in self:
            if rule.reward_point_split and (rule.program_id.applies_on == 'both' or rule.program_id.program_type == 'ewallet'):
                raise ValidationError(_('Split per unit is not allowed for Loyalty and eWallet programs.'))

    @api.constrains('code')
    def _constrains_code(self):
        mapped_codes = self.filtered('code').mapped('code')
        # Program code must be unique
        if len(mapped_codes) != len(set(mapped_codes)) or\
            self.env['loyalty.rule'].search_count(
                [('mode', '=', 'with_code'), ('code', 'in', mapped_codes), ('id', 'not in', self.ids)]):
            raise ValidationError(_('The promo code must be unique.'))
        # Prevent coupons and programs from sharing a code
        if self.env['loyalty.card'].search_count([('code', 'in', mapped_codes)]):
            raise ValidationError(_('A coupon with the same code was found.'))

    @api.depends('mode')
    def _compute_code(self):
        # Reset code when mode is set to auto
        for rule in self:
            if rule.mode == 'auto':
                rule.code = False

    @api.depends('code')
    def _compute_mode(self):
        for rule in self:
            if rule.code:
                rule.mode = 'with_code'
            else:
                rule.mode = 'auto'

    @api.depends_context('uid')
    @api.depends("mode")
    def _compute_user_has_debug(self):
        self.user_has_debug = self.user_has_groups('base.group_no_one')

    def _get_valid_product_domain(self):
        self.ensure_one()
        domain = []
        if self.product_ids:
            domain = [('id', 'in', self.product_ids.ids)]
        if self.product_category_id:
            domain = expression.OR([domain, [('categ_id', 'child_of', self.product_category_id.id)]])
        if self.product_tag_id:
            domain = expression.OR([domain, [('all_product_tag_ids', 'in', self.product_tag_id.id)]])
        if self.product_domain and self.product_domain != '[]':
            domain = expression.AND([domain, ast.literal_eval(self.product_domain)])
        return domain

    def _get_valid_products(self):
        self.ensure_one()
        return self.env['product.product'].search(self._get_valid_product_domain())

    def _compute_amount(self, currency_to):
        self.ensure_one()
        return self.currency_id._convert(
            self.minimum_amount,
            currency_to,
            self.company_id or self.env.company,
            fields.Date.today()
        )
