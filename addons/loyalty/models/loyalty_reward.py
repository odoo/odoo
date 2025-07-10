# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _description = "Loyalty Reward"
    _rec_name = 'description'
    _order = 'required_points asc'

    @api.model
    def default_get(self, fields):
        # Try to copy the values of the program types default's
        result = super().default_get(fields)
        if 'program_type' in self.env.context:
            program_type = self.env.context['program_type']
            program_default_values = self.env['loyalty.program']._program_type_default_values()
            if program_type in program_default_values and\
                len(program_default_values[program_type]['reward_ids']) == 2 and\
                isinstance(program_default_values[program_type]['reward_ids'][1][2], dict):
                result.update({
                    k: v for k, v in program_default_values[program_type]['reward_ids'][1][2].items() if k in fields
                })
        return result

    def _get_discount_mode_select(self):
        # The value is provided in the loyalty program's view since we may not have a program_id yet
        #  and makes sure to display the currency related to the program instead of the company's.
        symbol = self.env.context.get('currency_symbol', self.env.company.currency_id.symbol)
        return [
            ('percent', "%"),
            ('per_order', symbol),
            ('per_point', _("%s per point", symbol)),
        ]

    @api.depends('program_id', 'description')
    def _compute_display_name(self):
        for reward in self:
            reward.display_name = f"{reward.program_id.name} - {reward.description}"

    active = fields.Boolean(default=True)
    program_id = fields.Many2one(comodel_name='loyalty.program', ondelete='cascade', required=True, index=True)
    program_type = fields.Selection(related='program_id.program_type')
    # Stored for security rules
    company_id = fields.Many2one(related='program_id.company_id', store=True)
    currency_id = fields.Many2one(related='program_id.currency_id')

    description = fields.Char(
        translate=True,
        compute='_compute_description',
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )

    reward_type = fields.Selection(
        selection=[
            ('product', "Free Product"),
            ('discount', "Discount"),
        ],
        required=True,
        default='discount',
    )
    user_has_debug = fields.Boolean(compute='_compute_user_has_debug')

    # Discount rewards
    discount = fields.Float(string="Discount", default=10)
    discount_mode = fields.Selection(
        selection=_get_discount_mode_select, required=True, default='percent'
    )
    discount_applicability = fields.Selection(
        selection=[
            ('order', "Order"),
            ('cheapest', "Cheapest Product"),
            ('specific', "Specific Products"),
        ],
        default='order',
    )
    discount_product_domain = fields.Char(default="[]")
    discount_product_ids = fields.Many2many(
        string="Discounted Products", comodel_name='product.product'
    )
    discount_product_category_id = fields.Many2one(
        string="Discounted Prod. Categories", comodel_name='product.category'
    )
    discount_product_tag_id = fields.Many2one(
        string="Discounted Prod. Tag", comodel_name='product.tag'
    )
    all_discount_product_ids = fields.Many2many(
        comodel_name='product.product', compute='_compute_all_discount_product_ids'
    )
    reward_product_domain = fields.Char(compute='_compute_reward_product_domain', store=False)
    discount_max_amount = fields.Monetary(
        string="Max Discount",
        help="This is the max amount this reward may discount, leave to 0 for no limit.",
    )
    discount_line_product_id = fields.Many2one(
        help="Product used in the sales order to apply the discount. Each reward has its own"
             " product for reporting purpose",
        comodel_name='product.product',
        ondelete='restrict',
        copy=False,
    )
    is_global_discount = fields.Boolean(compute='_compute_is_global_discount')

    # Product rewards
    reward_product_id = fields.Many2one(
        string="Product", comodel_name='product.product', domain=[('type', '!=', 'combo')]
    )
    reward_product_tag_id = fields.Many2one(string="Product Tag", comodel_name='product.tag')
    multi_product = fields.Boolean(compute='_compute_multi_product')
    reward_product_ids = fields.Many2many(
        string="Reward Products",
        help="These are the products that can be claimed with this rule.",
        comodel_name='product.product',
        compute='_compute_multi_product',
        search='_search_reward_product_ids',
    )
    reward_product_qty = fields.Integer(default=1)
    reward_product_uom_id = fields.Many2one(
        comodel_name='uom.uom', compute='_compute_reward_product_uom_id'
    )

    required_points = fields.Float(string="Points needed", default=1)
    point_name = fields.Char(related='program_id.portal_point_name', readonly=True)
    clear_wallet = fields.Boolean(default=False)

    _required_points_positive = models.Constraint(
        'CHECK (required_points > 0)',
        "The required points for a reward must be strictly positive.",
    )
    _product_qty_positive = models.Constraint(
        "CHECK (reward_type != 'product' OR reward_product_qty > 0)",
        "The reward product quantity must be strictly positive.",
    )
    _discount_positive = models.Constraint(
        "CHECK (reward_type != 'discount' OR discount > 0)",
        "The discount must be strictly positive.",
    )

    @api.depends('reward_product_id.product_tmpl_id.uom_id', 'reward_product_tag_id')
    def _compute_reward_product_uom_id(self):
        for reward in self:
            reward.reward_product_uom_id = reward.reward_product_ids.product_tmpl_id.uom_id[:1]

    def _find_all_category_children(self, category_id, child_ids):
        if len(category_id.child_id) > 0:
            for child_id in category_id.child_id:
                child_ids.append(child_id.id)
                self._find_all_category_children(child_id, child_ids)
        return child_ids

    def _get_discount_product_domain(self):
        self.ensure_one()
        constrains = []
        if self.discount_product_ids:
            constrains.append([('id', 'in', self.discount_product_ids.ids)])
        if self.discount_product_category_id:
            product_category_ids = self._find_all_category_children(self.discount_product_category_id, [])
            product_category_ids.append(self.discount_product_category_id.id)
            constrains.append([('categ_id', 'in', product_category_ids)])
        if self.discount_product_tag_id:
            constrains.append([('all_product_tag_ids', 'in', self.discount_product_tag_id.id)])
        domain = Domain.OR(constrains) if constrains else Domain.TRUE
        if self.discount_product_domain and self.discount_product_domain != '[]':
            domain &= Domain(ast.literal_eval(self.discount_product_domain))
        return domain

    @api.model
    def _get_active_products_domain(self):
        return [
            '|',
                ('reward_type', '!=', 'product'),
                '&',
                    ('reward_type', '=', 'product'),
                    '|',
                        '&',
                            ('reward_product_tag_id', '=', False),
                            ('reward_product_id.active', '=', True),
                        '&',
                            ('reward_product_tag_id', '!=', False),
                            ('reward_product_ids.active', '=', True)
        ]

    @api.depends('discount_product_domain')
    def _compute_reward_product_domain(self):
        compute_all_discount_product = self.env['ir.config_parameter'].sudo().get_param('loyalty.compute_all_discount_product_ids', 'enabled')
        for reward in self:
            if compute_all_discount_product == 'enabled':
                reward.reward_product_domain = "null"
            else:
                reward.reward_product_domain = json.dumps(list(reward._get_discount_product_domain()))

    @api.depends('discount_product_ids', 'discount_product_category_id', 'discount_product_tag_id', 'discount_product_domain')
    def _compute_all_discount_product_ids(self):
        compute_all_discount_product = self.env['ir.config_parameter'].sudo().get_param('loyalty.compute_all_discount_product_ids', 'enabled')
        for reward in self:
            if compute_all_discount_product == 'enabled':
                reward.all_discount_product_ids = self.env['product.product'].search(reward._get_discount_product_domain())
            else:
                reward.all_discount_product_ids = self.env['product.product']

    @api.depends('reward_product_id', 'reward_product_tag_id', 'reward_type')
    def _compute_multi_product(self):
        for reward in self:
            products = reward.reward_product_id + reward.reward_product_tag_id.product_ids.filtered(
                lambda product: product.type != 'combo'
            )
            reward.multi_product = reward.reward_type == 'product' and len(products) > 1
            reward.reward_product_ids = reward.reward_type == 'product' and products or self.env['product.product']

    def _search_reward_product_ids(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [
            '&', ('reward_type', '=', 'product'),
            '|', ('reward_product_id', operator, value),
            ('reward_product_tag_id.product_ids', operator, value)
        ]

    @api.depends('reward_type', 'reward_product_id', 'discount_mode', 'reward_product_tag_id',
                 'discount', 'currency_id', 'discount_applicability', 'all_discount_product_ids')
    def _compute_description(self):
        for reward in self:
            reward_string = ""
            if reward.program_type == 'gift_card':
                reward_string = _("Gift Card")
            elif reward.program_type == 'ewallet':
                reward_string = _("eWallet")
            elif reward.reward_type == 'product':
                products = reward.reward_product_ids
                if len(products) == 0:
                    reward_string = _("Free Product")
                elif len(products) == 1:
                    reward_string = _("Free Product - %s", reward.reward_product_id.with_context(display_default_code=False).display_name)
                else:
                    reward_string = _("Free Product - [%s]", ', '.join(products.with_context(display_default_code=False).mapped('display_name')))
            elif reward.reward_type == 'discount':
                format_string = "%(amount)g %(symbol)s"
                if reward.currency_id.position == 'before':
                    format_string = "%(symbol)s %(amount)g"
                formatted_amount = format_string % {'amount': reward.discount, 'symbol': reward.currency_id.symbol}
                if reward.discount_mode == 'percent':
                    reward_string = _("%g%% on ", reward.discount)
                elif reward.discount_mode == 'per_point':
                    reward_string = _("%s per point on ", formatted_amount)
                elif reward.discount_mode == 'per_order':
                    reward_string = _("%s on ", formatted_amount)
                if reward.discount_applicability == 'order':
                    reward_string += _("your order")
                elif reward.discount_applicability == 'cheapest':
                    reward_string += _("the cheapest product")
                elif reward.discount_applicability == 'specific':
                    product_available = self.env['product.product'].search(reward._get_discount_product_domain(), limit=2)
                    if len(product_available) == 1:
                        reward_string += product_available.with_context(display_default_code=False).display_name
                    else:
                        reward_string += _("specific products")
                if reward.discount_max_amount:
                    format_string = "%(amount)g %(symbol)s"
                    if reward.currency_id.position == 'before':
                        format_string = "%(symbol)s %(amount)g"
                    formatted_amount = format_string % {'amount': reward.discount_max_amount, 'symbol': reward.currency_id.symbol}
                    reward_string += _(" (Max %s)", formatted_amount)
            reward.description = reward_string

    @api.depends('reward_type', 'discount_applicability', 'discount_mode')
    def _compute_is_global_discount(self):
        for reward in self:
            reward.is_global_discount = (
                reward.reward_type == 'discount'
                and reward.discount_applicability == 'order'
                and reward.discount_mode in ['per_order', 'percent']
            )

    @api.depends_context('uid')
    @api.depends('reward_type')
    def _compute_user_has_debug(self):
        self.user_has_debug = self.env.user.has_group('base.group_no_one')

    @api.constrains('reward_product_id')
    def _check_reward_product_id_no_combo(self):
        if any(reward.reward_product_id.type == 'combo' for reward in self):
            raise ValidationError(_("A reward product can't be of type \"combo\"."))

    def _create_missing_discount_line_products(self):
        # Make sure we create the product that will be used for our discounts
        rewards = self.filtered(lambda r: not r.discount_line_product_id)
        products = self.env['product.product'].create(rewards._get_discount_product_values())
        for reward, product in zip(rewards, products):
            reward.discount_line_product_id = product

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_missing_discount_line_products()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'description' in vals:
            self._create_missing_discount_line_products()
            # Keep the name of our discount product up to date
            for reward in self:
                reward.discount_line_product_id.write({'name': reward.description})
        if 'active' in vals:
            if vals['active']:
                self.discount_line_product_id.action_unarchive()
            else:
                self.discount_line_product_id.action_archive()
        return res

    def unlink(self):
        programs = self.program_id
        res = super().unlink()
        # Not guaranteed to trigger the constraint
        programs._constrains_reward_ids()
        return res

    def _get_discount_product_values(self):
        return [{
            'name': reward.description,
            'type': 'service',
            'sale_ok': False,
            'purchase_ok': False,
            'lst_price': 0,
        } for reward in self]
