from odoo import _, api, fields, models


class FidelityRule(models.Model):
    _name = 'fidelity.rule'
    _description = "Fidelity Rule"

    active = fields.Boolean(default=True)
    program_id = fields.Many2one(comodel_name='fidelity.program', ondelete='cascade', required=True, index=True)
    company_id = fields.Many2one(related='program_id.company_id')
    currency_id = fields.Many2one(related='program_id.currency_id')

    # Conditions
    minimum_qty = fields.Integer(string="Minimum Quantity", default=1)
    minimum_amount = fields.Monetary(string="Minimum Purchase")
    minimum_amount_tax_mode = fields.Selection(selection=[
            ('incl', "Tax included"),
            ('excl', "Tax excluded"),
        ],
        required=True,
        default='incl',
    )

    # Product applicability
    product_ids = fields.Many2many(string="Products", comodel_name='product.product')
    product_category_ids = fields.Many2many(string="Categories", comodel_name='product.category')
    product_tag_ids = fields.Many2many(string="Product Tags", comodel_name='product.tag')
    nb_products = fields.Integer(string="Products count", compute="_compute_nb_products")

    # Granted points
    reward_point_amount = fields.Float(string="Reward", default=1)
    reward_point_mode = fields.Selection(
        selection=[
            ('order', _("Order placed")),
            ('money', _("Per money spent")),
            ('unit', _("Per unit paid")),
        ],
        required=True,
        default='order',
    )

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
