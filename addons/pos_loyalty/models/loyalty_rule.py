# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _inherit = ['loyalty.rule', 'pos.load.mixin']

    valid_product_ids = fields.Many2many(
        'product.product', "Valid Products", compute='_compute_valid_product_ids',
        help="These are the products that are valid for this rule.")
    any_product = fields.Boolean(
        compute='_compute_valid_product_ids', help="Technical field, whether all product match")

    promo_barcode = fields.Char("Barcode", compute='_compute_promo_barcode', store=True, readonly=False,
        help="A technical field used as an alternative to the promo code. "
        "This is automatically generated when the promo code is changed."
    )
    pos_categ_id = fields.Many2one(string="POS Categories", comodel_name='pos.category')

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('program_id', 'in', config._get_program_ids().ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['program_id', 'valid_product_ids', 'any_product', 'currency_id',
            'reward_point_amount', 'reward_point_split', 'reward_point_mode',
            'minimum_qty', 'minimum_amount', 'minimum_amount_tax_mode', 'mode', 'code', 'pos_categ_id']

    @api.depends('product_ids', 'product_category_id', 'pos_categ_id', 'product_tag_id', 'product_domain')  # TODO later: product tags
    def _compute_valid_product_ids(self):
        for key, rules in self.grouped(lambda rule: (
            tuple(rule.product_ids.ids),
            rule.product_category_id.id,
            rule.pos_categ_id.id,
            rule.product_tag_id.id,
            '' if rule.product_domain in ('[]', "[['sale_ok', '=', True]]") else rule.product_domain,
        )).items():
            if any(key):
                domain = Domain.AND([[('available_in_pos', '=', True)], rules[:1]._get_valid_product_domain()])
                rules.valid_product_ids = self.env['product.product'].search(domain, order="id")
                rules.any_product = False
            else:
                rules.valid_product_ids = self.env['product.product']
                rules.any_product = True

    @api.depends('code')
    def _compute_promo_barcode(self):
        for rule in self:
            rule.promo_barcode = self.env['loyalty.card']._generate_code()

    def _get_valid_product_domain(self):
        domain = super()._get_valid_product_domain()
        if self.pos_categ_id:
            pos_category_ids = self.pos_categ_id.ids
            if self.pos_categ_id.child_ids:
                pos_category_ids.extend(self.pos_categ_id.child_ids.ids)
            if domain is Domain.TRUE:
                return Domain('pos_categ_ids', 'in', pos_category_ids)
            domain = Domain.OR([domain, Domain('pos_categ_ids', 'in', pos_category_ids)])
        return domain
