from odoo import _, api, fields, models


class FidelityReward(models.Model):
    _name = 'fidelity.reward'
    _description = "Fidelity Reward"

    name = fields.Char(string="Name", compute="_compute_name", readonly=True, store=True)
    active = fields.Boolean(default=True)
    program_id = fields.Many2one(comodel_name='fidelity.program', ondelete='cascade', required=True, index=True)
    company_id = fields.Many2one(related='program_id.company_id')
    currency_id = fields.Many2one(related='program_id.currency_id')
    point_unit = fields.Char(related='program_id.point_unit', readonly=True)

    # Rewards configuration
    amount = fields.Float(string="Amount", default=10)
    quantity = fields.Integer(string="Free Quantity", default=1)
    amount_max = fields.Monetary(string="Max Discount", default=0, help="Max discount amount, leave to 0 for no limit.")
    type = fields.Selection(
        selection=[
            ('free', "Free Product"),
            ('discount', "Discount"),
        ],
        required=True,
        default='discount',
    )
    amount_type = fields.Selection(
        selection=[
            ('percent', "Percentage"),
            ('fixed', "Fixed Amount"),
        ],
        required=True,
        default='percent',
    )
    amount_applicability = fields.Selection(
        selection=[
            ('order', "Order"),
            ('cheapest', "Cheapest Product"),
            ('specific', "Specific Products"),
        ],
        default='order',
    )

    # Product applicability
    product_ids = fields.Many2many('product.product', string="Products")
    product_category_ids = fields.Many2many('product.category', string="Product Categories")
    product_tag_ids = fields.Many2many('product.tag', string="Product Tags")
    nb_products = fields.Integer(string="Products count", compute="_compute_nb_products")

    # Points usage
    required_points = fields.Float(string="Points needed", default=1)
    clear_wallet = fields.Boolean(default=False)

    @api.depends('product_ids', 'product_category_ids', 'product_tag_ids')
    def _compute_nb_products(self):
        for reward in self:
            domain = [('active', '=', True)]
            if reward.product_ids:
                domain.append(('id', 'in', reward.product_ids.ids))
            if reward.product_category_ids:
                domain.append(('categ_id', 'in', reward.product_category_ids.ids))
            if reward.product_tag_ids:
                domain.append(('tag_ids', 'in', reward.product_tag_ids.ids))
            reward.nb_products = self.env['product.product'].search_count(domain)

    @api.depends(
        'type',
        'quantity',
        'amount',
        'amount_type',
        'amount_applicability',
    )
    def _compute_name(self):
        for reward in self:
            string = ""
            if reward.type == 'discount':
                is_specific = reward.amount_applicability != 'order'
                symbol = reward.currency_id.symbol if reward.amount_type == 'fixed' else 'percents'
                string += _("Get a discount of %(amount)s %(symbol)s", amount=reward.amount, symbol=symbol)
                string += _(" on specific products") if is_specific else _(" on your order")
            else:
                string += _("Get %(quantity)d free product(s)", quantity=reward.quantity)
            reward.name = string
