# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.fields import Domain


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        pricelist_ids = [preset['pricelist_id'] for preset in data['pos.preset']]
        all_ids = config._get_available_pricelists().ids + pricelist_ids
        referenced_base_pricelist_ids = self.env['product.pricelist.item'].search([
            ('pricelist_id', 'in', all_ids),
            ('base', '=', 'pricelist'),
            ('base_pricelist_id', '!=', False),
        ]).base_pricelist_id.ids
        return [('id', 'in', list(set(all_ids + referenced_base_pricelist_ids)))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'display_name', 'currency_id', 'item_ids']

    def _get_applicable_rules_domain(self, products, *, date=None, quantity=None, uom=None, **_kwargs):
        # Filter out rules specific to pos categories
        base_domain = super()._get_applicable_rules_domain(products, date=date, quantity=quantity, uom=uom, **_kwargs)
        return Domain.AND([
            base_domain, Domain('applied_on', '!=', '4_pos_category')
        ])


class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'pos.load.mixin']

    applied_on = fields.Selection(
        selection_add=[('4_pos_category', "PoS Category")],
        ondelete={'4_pos_category': 'set default'})
    display_applied_on = fields.Selection(
        selection_add=[('4_pos_category', "PoS Category")],
        ondelete={'4_pos_category': 'set default'})
    pos_categ_id = fields.Many2one(
        comodel_name='pos.category',
        string="PoS Category",
        ondelete='cascade',
        help="Specify a pos category if this rule only applies to products belonging to this category or its children categories. If no category is specified, the rule will apply to all products.")

    @api.model
    def _load_pos_data_domain(self, data, config):
        pricelist_ids = [p['id'] for p in data['product.pricelist']]
        domain = [('pricelist_id', 'in', pricelist_ids)]

        if not self._last_server_date_to_load():
            product_tmpl_ids = [p['product_tmpl_id'] for p in data['product.product']]
            product_ids = [p['id'] for p in data['product.product']]
            product_categ = [c['id'] for c in data['product.category']]
            pos_product_categ = [c['id'] for c in data['pos.category']]
            now = fields.Datetime.now()
            domain += [
                '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
                '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
                '|', ('categ_id', '=', False), ('categ_id', 'in', product_categ),
                '|', ('pos_categ_id', '=', False), ('pos_categ_id', 'in', pos_product_categ),
                '|', ('date_start', '=', False), ('date_start', '<=', now),
                '|', ('date_end', '=', False), ('date_end', '>', now),
            ]
        return domain

    @api.model
    def _server_date_to_domain(self, domain):
        if last_server_date := self._last_server_date_to_load():
            now = fields.Datetime.now()
            domain = Domain.AND([
                domain,
                Domain.OR([
                    [('write_date', '>', last_server_date)],
                    ['&', ('date_start', '>', last_server_date), ('date_start', '<=', now)],
                ]),
            ])
        return domain

    @api.model
    def _load_pos_data_fields(self, config):
        return ['product_tmpl_id', 'product_id', 'pricelist_id', 'price_surcharge', 'price_discount', 'price_round',
                'price_min_margin', 'price_max_margin', 'company_id', 'currency_id', 'date_start', 'date_end', 'compute_price',
                'fixed_price', 'percent_price', 'base_pricelist_id', 'base', 'categ_id', 'min_quantity', 'uom_id', 'pos_categ_id']

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'pos_categ_id')
    def _compute_name(self):
        super()._compute_name()
        for item in self:
            if item.display_applied_on == '4_pos_category':
                item.name = item.pos_categ_id.display_name if item.pos_categ_id else _("All PoS Categories")

    @api.onchange('display_applied_on')
    def _onchange_display_applied_on(self):
        super()._onchange_display_applied_on()
        for item in self:
            # If set to apply based on POS category, reset other fields
            if item.display_applied_on == '4_pos_category':
                item.update({
                    'applied_on': '4_pos_category' if item.pos_categ_id else '3_global',
                    'product_id': None,
                    'product_tmpl_id': None,
                    'categ_id': None,
                    'product_uom_name': None,
                })
            else:
                item.update({'pos_categ_id': None})

    @api.onchange('product_id', 'product_tmpl_id', 'categ_id', 'pos_categ_id')
    def _onchange_rule_content(self):
        super()._onchange_rule_content()
        if not self.env.context.get('default_applied_on', False):
            self.filtered(lambda cat: bool(cat.pos_categ_id)).update({'applied_on': '4_pos_category'})

    def _is_applicable_for(self, product, quantity, *, uom=None, **_kwargs):
        res = super()._is_applicable_for(product, quantity, uom=uom, **_kwargs)
        if self.applied_on == "4_pos_category":
            if not product.pos_categ_ids or self.pos_categ_id.id not in [*product.pos_categ_ids.ids, *product.pos_categ_ids.child_ids.ids]:
                res = False
        return res
