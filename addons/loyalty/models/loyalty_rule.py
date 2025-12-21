# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _description = "Loyalty Rule"

    @api.model
    def default_get(self, fields):
        # Try to copy the values of the program types default's
        result = super().default_get(fields)
        if 'program_type' in self.env.context:
            program_type = self.env.context['program_type']
            program_default_values = self.env['loyalty.program']._program_type_default_values()
            if program_type in program_default_values and\
                len(program_default_values[program_type]['rule_ids']) == 2 and\
                isinstance(program_default_values[program_type]['rule_ids'][1][2], dict):
                result.update({
                    k: v for k, v in program_default_values[program_type]['rule_ids'][1][2].items() if k in fields
                })
        return result

    def _get_reward_point_mode_selection(self):
        # The value is provided in the loyalty program's view since we may not have a program_id yet
        #  and makes sure to display the currency related to the program instead of the company's.
        symbol = self.env.context.get('currency_symbol', self.env.company.currency_id.symbol)
        return [
            ('order', _("per order")),
            ('money', _("per %s spent", symbol)),
            ('unit', _("per unit paid")),
        ]

    active = fields.Boolean(default=True)
    program_id = fields.Many2one(comodel_name='loyalty.program', ondelete='cascade', required=True, index=True)
    program_type = fields.Selection(related='program_id.program_type')
    # Stored for security rules
    company_id = fields.Many2one(related='program_id.company_id', store=True)
    currency_id = fields.Many2one(related='program_id.currency_id')

    # Only for dev mode
    user_has_debug = fields.Boolean(compute='_compute_user_has_debug')
    product_domain = fields.Char(default="[]")

    product_ids = fields.Many2many(string="Products", comodel_name='product.product')
    product_category_id = fields.Many2one(string="Categories", comodel_name='product.category')
    product_tag_id = fields.Many2one(string="Product Tag", comodel_name='product.tag')

    reward_point_amount = fields.Float(string="Reward", default=1)
    # Only used for program_id.applies_on == 'future'
    reward_point_split = fields.Boolean(
        string="Split per unit",
        help="Whether to separate reward coupons per matched unit, only applies to 'future' programs and trigger mode per money spent or unit paid...",
        default=False,
    )
    reward_point_name = fields.Char(related='program_id.portal_point_name', readonly=True)
    reward_point_mode = fields.Selection(
        selection=_get_reward_point_mode_selection, required=True, default='order'
    )

    minimum_qty = fields.Integer(string="Minimum Quantity", default=1)
    minimum_amount = fields.Monetary(string="Minimum Purchase")
    minimum_amount_tax_mode = fields.Selection(
        selection=[
            ('incl', "tax included"),
            ('excl', "tax excluded"),
        ],
        required=True,
        default='incl',
    )

    mode = fields.Selection(
        string="Application",
        selection=[
            ('auto', "Automatic"),
            ('with_code', "With a promotion code"),
        ],
        compute='_compute_mode',
        store=True,
        readonly=False,
    )
    code = fields.Char(string="Discount code", compute='_compute_code', store=True, readonly=False)

    _reward_point_amount_positive = models.Constraint(
        'CHECK (reward_point_amount > 0)',
        "Rule points reward must be strictly positive.",
    )

    @api.constrains('reward_point_split')
    def _constraint_trigger_multi(self):
        # Prevent setting trigger multi in case of nominative programs, it does not make sense to allow this
        for rule in self:
            if rule.reward_point_split and (rule.program_id.applies_on == 'both' or rule.program_id.program_type == 'ewallet'):
                raise ValidationError(_("Split per unit is not allowed for Loyalty and eWallet programs."))

    @api.constrains('code', 'active')
    def _constrains_code(self):
        mapped_codes = self.filtered(lambda r: r.code and r.active).mapped('code')
        # Program code must be unique
        if len(mapped_codes) != len(set(mapped_codes)) or\
            self.env['loyalty.rule'].search_count([
                ('mode', '=', 'with_code'),
                ('code', 'in', mapped_codes),
                ('id', 'not in', self.ids),
                ('active', '=', True),
            ]):
            raise ValidationError(_("The promo code must be unique."))
        # Prevent coupons and programs from sharing a code
        if self.env['loyalty.card'].search_count([
            ('code', 'in', mapped_codes), ('active', '=', True)
        ]):
            raise ValidationError(_("A coupon with the same code was found."))

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
    @api.depends('mode')
    def _compute_user_has_debug(self):
        self.user_has_debug = self.env.user.has_group('base.group_no_one')

    def _get_valid_product_domain(self):
        self.ensure_one()
        constrains = []
        if self.product_ids:
            constrains.append([('id', 'in', self.product_ids.ids)])
        if self.product_category_id:
            constrains.append([('categ_id', 'child_of', self.product_category_id.id)])
        if self.product_tag_id:
            constrains.append([('all_product_tag_ids', 'in', self.product_tag_id.id)])
        domain = Domain.OR(constrains) if constrains else Domain.TRUE
        if self.product_domain and self.product_domain != '[]':
            domain &= Domain(ast.literal_eval(self.product_domain))
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
