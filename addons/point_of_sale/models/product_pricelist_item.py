# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'pos.load.mixin']

    applied_on = fields.Selection(
        selection_add=[('4_pos_category', "POS Category")],
        ondelete={'4_pos_category': 'set default'})
    display_applied_on = fields.Selection(
        selection_add=[('4_pos_category', "POS Category")],
        ondelete={'4_pos_category': 'set default'})
    pos_categ_id = fields.Many2one(
        comodel_name='pos.category',
        string="POS Category",
        ondelete='cascade',
        help="Specify a pos category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")

    @api.model
    def _load_pos_data_domain(self, data, config):
        product_tmpl_ids = [p['product_tmpl_id'] for p in data['product.product']]
        product_ids = [p['id'] for p in data['product.product']]
        product_categ = [c['id'] for c in data['product.category']]
        product_pos_categ = [c['id'] for c in data['pos.category']]
        pricelist_ids = [p['id'] for p in data['product.pricelist']]
        now = fields.Datetime.now()
        return [
            ('pricelist_id', 'in', pricelist_ids),
            '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
            '|', ('date_start', '=', False), ('date_start', '<=', now),
            '|', ('date_end', '=', False), ('date_end', '>=', now),
            '|', ('categ_id', '=', False), ('categ_id', 'in', product_categ),
            '|', ('pos_categ_id', '=', False), ('pos_categ_id', 'in', product_pos_categ),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['product_tmpl_id', 'product_id', 'pricelist_id', 'price_surcharge', 'price_discount', 'price_round',
                'price_min_margin', 'price_max_margin', 'company_id', 'currency_id', 'date_start', 'date_end', 'compute_price',
                'fixed_price', 'percent_price', 'base_pricelist_id', 'base', 'categ_id', 'pos_categ_id', 'min_quantity']

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'pos_categ_id')
    def _compute_name(self):
        res = super()._compute_name()
        for item in self.filtered(lambda i: i.applied_on == '4_pos_category'):
            item.name = item.pos_categ_id.display_name
        return res

    @api.onchange('display_applied_on')
    def _onchange_display_applied_on(self):
        res = super()._onchange_display_applied_on()
        pos_categ_items = self.filtered(lambda r: r.display_applied_on == '4_pos_category')
        other_items = self - pos_categ_items
        # If set to apply based on POS category, reset other fields
        pos_categ_items.update({
            'applied_on': '4_pos_category',
            'product_id': None,
            'product_tmpl_id': None,
            'categ_id': None,
            'product_uom_name': None,
        })
        # if not applicable based on POS category, remove pos_categ_id
        other_items.update({'pos_categ_id': None})
        return res

    @api.onchange('product_id', 'product_tmpl_id', 'categ_id', 'pos_categ_id')
    def _onchange_rule_content(self):
        res = super()._onchange_rule_content()
        if not self.env.context.get('default_applied_on', False):
            self.filtered(lambda cat: bool(cat.pos_categ_id)).update({'applied_on': '4_pos_category'})
        return res
