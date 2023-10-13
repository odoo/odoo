# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from uuid import uuid4

class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _description = 'Loyalty Program'
    _order = 'sequence'
    _rec_name = 'name'

    name = fields.Char('Program Name', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id',
        readonly=False, required=True, store=True, precompute=True)
    currency_symbol = fields.Char(related='currency_id.symbol')
    pricelist_ids = fields.Many2many(
        'product.pricelist', string="Pricelist", domain="[('currency_id', '=', currency_id)]"
    )

    total_order_count = fields.Integer("Total Order Count", compute="_compute_total_order_count")

    rule_ids = fields.One2many('loyalty.rule', 'program_id', 'Conditional rules', copy=True,
         compute='_compute_from_program_type', readonly=False, store=True)
    reward_ids = fields.One2many('loyalty.reward', 'program_id', 'Rewards', copy=True,
         compute='_compute_from_program_type', readonly=False, store=True)
    communication_plan_ids = fields.One2many('loyalty.mail', 'program_id', copy=True,
         compute='_compute_from_program_type', readonly=False, store=True)

    # These fields are used for the simplified view of gift_card and ewallet
    mail_template_id = fields.Many2one('mail.template', compute='_compute_mail_template_id', inverse='_inverse_mail_template_id', string="Email template", readonly=False)
    trigger_product_ids = fields.Many2many(related='rule_ids.product_ids', readonly=False)

    coupon_ids = fields.One2many('loyalty.card', 'program_id')
    coupon_count = fields.Integer(compute='_compute_coupon_count')
    coupon_count_display = fields.Char(compute='_compute_coupon_count_display', string="Items")

    program_type = fields.Selection([
        ('coupons', 'Coupons'),
        ('gift_card', 'Gift Card'),
        ('loyalty', 'Loyalty Cards'),
        ('promotion', 'Promotions'),
        ('ewallet', 'eWallet'),
        ('promo_code', 'Discount Code'),
        ('buy_x_get_y', 'Buy X Get Y'),
        ('next_order_coupons', 'Next Order Coupons')],
        default='promotion', required=True,
    )
    date_from = fields.Date(
        string="Start Date",
        help="The start date is included in the validity period of this program",
    )
    date_to = fields.Date(
        string="End date",
        help="The end date is included in the validity period of this program",
    )
    limit_usage = fields.Boolean(string='Limit Usage')
    max_usage = fields.Integer()
    # Dictates when the points can be used:
    # current: if the order gives enough points on that order, the reward may directly be claimed, points lost otherwise
    # future: if the order gives enough points on that order, a coupon is generated for a next order
    # both: points are accumulated on the coupon to claim rewards, the reward may directly be claimed
    applies_on = fields.Selection([
        ('current', 'Current order'),
        ('future', 'Future orders'),
        ('both', 'Current & Future orders')], default='current', required=True,
         compute='_compute_from_program_type', readonly=False, store=True,
    )
    trigger = fields.Selection([
        ('auto', 'Automatic'),
        ('with_code', 'Use a code')],
        compute='_compute_from_program_type', readonly=False, store=True,
        help="""
        Automatic: Customers will be eligible for a reward automatically in their cart.
        Use a code: Customers will be eligible for a reward if they enter a code.
        """
    )
    portal_visible = fields.Boolean(default=False,
        help="""
        Show in web portal, PoS customer ticket, eCommerce checkout, the number of points available and used by reward.
        """)
    portal_point_name = fields.Char(default='Points', translate=True,
         compute='_compute_portal_point_name', readonly=False, store=True)
    is_nominative = fields.Boolean(compute='_compute_is_nominative')
    is_payment_program = fields.Boolean(compute='_compute_is_payment_program')

    payment_program_discount_product_id = fields.Many2one(
        'product.product',
        string='Discount Product',
        compute='_compute_payment_program_discount_product_id',
        readonly=True,
        help="Product used in the sales order to apply the discount."
    )

    # Technical field used for a label
    available_on = fields.Boolean("Available On", store=False,
        help="""
        Manage where your program should be available for use.
        """
    )

    _sql_constraints = [
        ('check_max_usage', 'CHECK (limit_usage = False OR max_usage > 0)',
            'Max usage must be strictly positive if a limit is used.'),
    ]

    @api.constrains('currency_id', 'pricelist_ids')
    def _check_pricelist_currency(self):
        if any(
            pricelist.currency_id != program.currency_id
            for program in self
            for pricelist in program.pricelist_ids
        ):
            raise UserError(_(
                "The loyalty program's currency must be the same as all it's pricelists ones."
            ))

    @api.constrains('date_from', 'date_to')
    def _check_date_from_date_to(self):
        if any(p.date_to and p.date_from and p.date_from > p.date_to for p in self):
            raise UserError(_(
                "The validity period's start date must be anterior or equal to its end date."
            ))

    @api.constrains('reward_ids')
    def _constrains_reward_ids(self):
        if self.env.context.get('loyalty_skip_reward_check'):
            return
        if any(not program.reward_ids for program in self):
            raise ValidationError(_('A program must have at least one reward.'))

    def _compute_total_order_count(self):
        self.total_order_count = 0

    @api.depends('coupon_count', 'program_type')
    def _compute_coupon_count_display(self):
        program_items_name = self._program_items_name()
        for program in self:
            program.coupon_count_display = "%i %s" % (program.coupon_count or 0, program_items_name[program.program_type] or '')

    @api.depends("communication_plan_ids.mail_template_id")
    def _compute_mail_template_id(self):
        for program in self:
            program.mail_template_id = program.communication_plan_ids.mail_template_id[:1]

    def _inverse_mail_template_id(self):
        for program in self:
            if program.program_type not in ("gift_card", "ewallet"):
                continue
            if not program.mail_template_id:
                program.communication_plan_ids = [(5, 0, 0)]
            elif not program.communication_plan_ids:
                program.communication_plan_ids = self.env['loyalty.mail'].create({
                    'program_id': program.id,
                    'trigger': 'create',
                    'mail_template_id': program.mail_template_id.id,
                })
            else:
                program.communication_plan_ids.write({
                    'trigger': 'create',
                    'mail_template_id': program.mail_template_id.id,
                })

    @api.depends('company_id')
    def _compute_currency_id(self):
        for program in self:
            program.currency_id = program.company_id.currency_id or program.currency_id

    @api.depends('coupon_ids')
    def _compute_coupon_count(self):
        read_group_data = self.env['loyalty.card']._read_group([('program_id', 'in', self.ids)], ['program_id'], ['__count'])
        count_per_program = {program.id: count for program, count in read_group_data}
        for program in self:
            program.coupon_count = count_per_program.get(program.id, 0)

    @api.depends('program_type', 'applies_on')
    def _compute_is_nominative(self):
        for program in self:
            program.is_nominative = program.applies_on == 'both' or\
                (program.program_type == 'ewallet' and program.applies_on == 'future')

    @api.depends('program_type')
    def _compute_is_payment_program(self):
        for program in self:
            program.is_payment_program = program.program_type in ('gift_card', 'ewallet')

    @api.depends('reward_ids.discount_line_product_id')
    def _compute_payment_program_discount_product_id(self):
        for program in self:
            if program.is_payment_program:
                program.payment_program_discount_product_id = program.reward_ids[0].discount_line_product_id
            else:
                program.payment_program_discount_product_id = False

    @api.model
    def _program_items_name(self):
        return {
            'coupons': _('Coupons'),
            'promotion': _('Promos'),
            'gift_card': _('Gift Cards'),
            'loyalty': _('Loyalty Cards'),
            'ewallet': _('eWallets'),
            'promo_code': _('Discounts'),
            'buy_x_get_y': _('Promos'),
            'next_order_coupons': _('Coupons'),
        }

    @api.model
    def _program_type_default_values(self):
        # All values to change when program_type changes
        # NOTE: any field used in `rule_ids`, `reward_ids` and `communication_plan_ids` MUST be present in the kanban view for it to work properly.
        first_sale_product = self.env['product.product'].search([('company_id', 'in', [False, self.env.company.id]), ('sale_ok', '=', True)], limit=1)
        return {
            'coupons': {
                'applies_on': 'current',
                'trigger': 'with_code',
                'portal_visible': False,
                'portal_point_name': _('Coupon point(s)'),
                'rule_ids': [(5, 0, 0)],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'required_points': 1,
                    'discount': 10,
                })],
                'communication_plan_ids': [(5, 0, 0), (0, 0, {
                    'trigger': 'create',
                    'mail_template_id': (self.env.ref('loyalty.mail_template_loyalty_card', raise_if_not_found=False) or self.env['mail.template']).id,
                })],
            },
            'promotion': {
                'applies_on': 'current',
                'trigger': 'auto',
                'portal_visible': False,
                'portal_point_name': _('Promo point(s)'),
                'rule_ids': [(5, 0, 0), (0, 0, {
                    'reward_point_amount': 1,
                    'reward_point_mode': 'order',
                    'minimum_amount': 50,
                    'minimum_qty': 0,
                })],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'required_points': 1,
                    'discount': 10,
                })],
                'communication_plan_ids': [(5, 0, 0)],
            },
            'gift_card': {
                'applies_on': 'future',
                'trigger': 'auto',
                'portal_visible': True,
                'portal_point_name': self.env.company.currency_id.symbol,
                'rule_ids': [(5, 0, 0), (0, 0, {
                    'reward_point_amount': 1,
                    'reward_point_mode': 'money',
                    'reward_point_split': True,
                    'product_ids': self.env.ref('loyalty.gift_card_product_50', raise_if_not_found=False),
                    'minimum_qty': 0,
                })],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'reward_type': 'discount',
                    'discount_mode': 'per_point',
                    'discount': 1,
                    'discount_applicability': 'order',
                    'required_points': 1,
                    'description': _('Gift Card'),
                })],
                'communication_plan_ids': [(5, 0, 0), (0, 0, {
                    'trigger': 'create',
                    'mail_template_id': (self.env.ref('loyalty.mail_template_gift_card', raise_if_not_found=False) or self.env['mail.template']).id,
                })],
            },
            'loyalty': {
                'applies_on': 'both',
                'trigger': 'auto',
                'portal_visible': True,
                'portal_point_name': _('Loyalty point(s)'),
                'rule_ids': [(5, 0, 0), (0, 0, {
                    'reward_point_mode': 'money',
                })],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'discount': 5,
                    'required_points': 200,
                })],
                'communication_plan_ids': [(5, 0, 0)],
            },
            'ewallet': {
                'trigger': 'auto',
                'applies_on': 'future',
                'portal_visible': True,
                'portal_point_name': self.env.company.currency_id.symbol,
                'rule_ids': [(5, 0, 0), (0, 0, {
                    'reward_point_amount': '1',
                    'reward_point_mode': 'money',
                    'reward_point_split': False,
                    'product_ids': self.env.ref('loyalty.ewallet_product_50', raise_if_not_found=False),
                })],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'reward_type': 'discount',
                    'discount_mode': 'per_point',
                    'discount': 1,
                    'discount_applicability': 'order',
                    'required_points': 1,
                    'description': _('eWallet'),
                })],
                'communication_plan_ids': [(5, 0, 0)],
            },
            'promo_code': {
                'applies_on': 'current',
                'trigger': 'with_code',
                'portal_visible': False,
                'portal_point_name': _('Discount point(s)'),
                'rule_ids': [(5, 0, 0), (0, 0, {
                    'mode': 'with_code',
                    'code': 'PROMO_CODE_' + str(uuid4())[:4], # We should try not to trigger any unicity constraint
                    'minimum_qty': 0,
                })],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'discount_applicability': 'specific',
                    'discount_product_ids': first_sale_product,
                    'discount_mode': 'percent',
                    'discount': 10,
                })],
                'communication_plan_ids': [(5, 0, 0)],
            },
            'buy_x_get_y': {
                'applies_on': 'current',
                'trigger': 'auto',
                'portal_visible': False,
                'portal_point_name': _('Credit(s)'),
                'rule_ids': [(5, 0, 0), (0, 0, {
                    'reward_point_mode': 'unit',
                    'product_ids': first_sale_product,
                    'minimum_qty': 2,
                })],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'reward_type': 'product',
                    'reward_product_id': first_sale_product.id,
                    'required_points': 2,
                })],
                'communication_plan_ids': [(5, 0, 0)],
            },
            'next_order_coupons': {
                'applies_on': 'future',
                'trigger': 'auto',
                'portal_visible': True,
                'portal_point_name': _('Coupon point(s)'),
                'rule_ids': [(5, 0, 0), (0, 0, {
                    'minimum_amount': 100,
                    'minimum_qty': 0,
                })],
                'reward_ids': [(5, 0, 0), (0, 0, {
                    'reward_type': 'discount',
                    'discount_mode': 'percent',
                    'discount': 15,
                    'discount_applicability': 'order',
                })],
                'communication_plan_ids': [(5, 0, 0), (0, 0, {
                    'trigger': 'create',
                    'mail_template_id': (
                        self.env.ref('loyalty.mail_template_loyalty_card', raise_if_not_found=False)
                        or self.env['mail.template']
                    ).id,
                })],
            },
        }

    @api.depends('program_type')
    def _compute_from_program_type(self):
        program_type_defaults = self._program_type_default_values()
        grouped_programs = defaultdict(lambda: self.env['loyalty.program'])
        for program in self:
            grouped_programs[program.program_type] |= program
        for program_type, programs in grouped_programs.items():
            if program_type in program_type_defaults:
                programs.write(program_type_defaults[program_type])

    @api.depends("currency_id", "program_type")
    def _compute_portal_point_name(self):
        for program in self:
            if program.program_type not in ('ewallet', 'gift_card'):
                continue
            program.portal_point_name = program.currency_id.symbol or ''

    def _get_valid_products(self, products):
        '''
        Returns a dict containing the products that match per rule of the program
        '''
        rule_products = dict()
        for rule in self.rule_ids:
            domain = rule._get_valid_product_domain()
            if domain:
                rule_products[rule] = products.filtered_domain(domain)
            else:
                rule_products[rule] = products
        return rule_products

    def action_open_loyalty_cards(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id("loyalty.loyalty_card_action")
        action['name'] = self._program_items_name()[self.program_type]
        action['display_name'] = action['name']
        action['context'] = {
            'program_type': self.program_type,
            'program_item_name': self._program_items_name()[self.program_type],
            'default_program_id': self.id,
            # For the wizard
            'default_mode': self.program_type == 'ewallet' and 'selected' or 'anonymous',
        }
        return action

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active(self):
        if any(program.active for program in self):
            raise UserError(_('You can not delete a program in an active state'))

    def toggle_active(self):
        res = super().toggle_active()
        # Propagate active state to children
        for program in self.with_context(active_test=False):
            program.rule_ids.active = program.active
            program.reward_ids.active = program.active
            program.communication_plan_ids.active = program.active
            program.reward_ids.with_context(active_test=True).discount_line_product_id.active = program.active
        return res

    def write(self, vals):
        # There is an issue when we change the program type, since we clear the rewards and create new ones.
        # The orm actually does it in this order upon writing, triggering the constraint before creating the new rewards.
        # However we can check that the result of reward_ids would actually be empty or not, and if not, skip the constraint.
        if 'reward_ids' in vals and self._fields['reward_ids'].convert_to_cache(vals['reward_ids'], self):
            self = self.with_context(loyalty_skip_reward_check=True)
            # We need add the program type to the context to avoid getting the default value
            # ('discount') for reward type when calling the `default_get` method of
            #`loyalty.reward`.
            if 'program_type' in vals:
                self = self.with_context(program_type=vals['program_type'])
                return super().write(vals)
            else:
                for program in self:
                    program = program.with_context(program_type=program.program_type)
                    super(LoyaltyProgram, program).write(vals)
                return True
        else:
            return super().write(vals)

    @api.model
    def get_program_templates(self):
        '''
        Returns the templates to be used for promotional programs.
        '''
        ctx_menu_type = self.env.context.get('menu_type')
        if ctx_menu_type == 'gift_ewallet':
            return {
                'gift_card': {
                    'title': _("Gift Card"),
                    'description': _("Sell Gift Cards, that allows to purchase products"),
                    'icon': 'gift_card',
                },
                'ewallet': {
                    'title': _("eWallet"),
                    'description': _("Fill in your eWallet, to pay future orders"),
                    'icon': 'ewallet',
                },
            }
        return {
            'promotion': {
                'title': _("Promotional Program"),
                'description': _("Automatic promo: 10% off on orders higher than $50"),
                'icon': 'promotional_program',
            },
            'promo_code': {
                'title': _("Promo Code"),
                'description': _("Get 10% off on some products, with a code"),
                'icon': 'promo_code',
            },
            'buy_x_get_y': {
                'title': _("Buy X Get Y"),
                'description': _("Buy 2 products and get a third one for free"),
                'icon': '2_plus_1',
            },
            'next_order_coupons': {
                'title': _("Next Order Coupon"),
                'description': _("Send a coupon after an order, valid for next purchase"),
                'icon': 'coupons',
            },
            'loyalty': {
                'title': _("Loyalty Card"),
                'description': _("Win points with each purchase, and claim gifts"),
                'icon': 'loyalty_cards',
            },
            'coupons': {
                'title': _("Coupon"),
                'description': _("Generate and share unique coupons with your customers"),
                'icon': 'coupons',
            },
            'fidelity': {
                'title': _("Fidelity Card"),
                'description': _("Buy 10 products to get 10$ off on the 11th one"),
                'icon': 'fidelity_cards',
            },
        }

    @api.model
    def create_from_template(self, template_id):
        '''
        Creates the program from the template id defined in `get_program_templates`.

        Returns an action leading to that new record.
        '''
        template_values = self._get_template_values()
        if template_id not in template_values:
            return False
        program = self.create(template_values[template_id])
        action = {}
        if self.env.context.get('menu_type') == 'gift_ewallet':
            action = self.env['ir.actions.act_window']._for_xml_id('loyalty.loyalty_program_gift_ewallet_action')
            action['views'] = [[False, 'form']]
        else:
            action = self.env['ir.actions.act_window']._for_xml_id('loyalty.loyalty_program_discount_loyalty_action')
            view_id = self.env.ref('loyalty.loyalty_program_view_form').id
            action['views'] = [[view_id, 'form']]
        action['view_mode'] = 'form'
        action['res_id'] = program.id
        return action

    @api.model
    def _get_template_values(self):
        '''
        Returns the values to create a program using the template keys defined above.
        '''
        program_type_defaults = self._program_type_default_values()
        # For programs that require a product get the first sellable.
        product = self.env['product.product'].search([('sale_ok', '=', True)], limit=1)
        return {
            'gift_card': {
                'name': _('Gift Card'),
                'program_type': 'gift_card',
                **program_type_defaults['gift_card']
            },
            'ewallet': {
                'name': _('eWallet'),
                'program_type': 'ewallet',
                **program_type_defaults['ewallet'],
            },
            'loyalty': {
                'name': _('Loyalty Cards'),
                'program_type': 'loyalty',
                **program_type_defaults['loyalty'],
            },
            'coupons': {
                'name': _('Coupons'),
                'program_type': 'coupons',
                **program_type_defaults['coupons'],
            },
            'promotion': {
                'name': _('Promotional Program'),
                'program_type': 'promotion',
                **program_type_defaults['promotion'],
            },
            'promo_code': {
                'name': _('Discount code'),
                'program_type': 'promo_code',
                **program_type_defaults['promo_code'],
            },
            'buy_x_get_y': {
                'name': _('2+1 Free'),
                'program_type': 'buy_x_get_y',
                **program_type_defaults['buy_x_get_y'],
            },
            'next_order_coupons': {
                'name': _('Next Order Coupons'),
                'program_type': 'next_order_coupons',
                **program_type_defaults['next_order_coupons'],
            },
            'fidelity': {
                'name': _('Fidelity Cards'),
                'program_type': 'loyalty',
                'applies_on': 'both',
                'trigger': 'auto',
                'rule_ids': [(0, 0, {
                    'reward_point_mode': 'unit',
                    'product_ids': product,
                })],
                'reward_ids': [(0, 0, {
                    'discount_mode': 'per_order',
                    'required_points': 11,
                    'discount_applicability': 'specific',
                    'discount_product_ids': product,
                    'discount': 10,
                })]
            },
        }
