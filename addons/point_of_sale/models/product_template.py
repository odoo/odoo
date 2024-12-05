# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import SQL
from itertools import groupby
from operator import itemgetter
from datetime import date


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'pos.load.mixin']

    available_in_pos = fields.Boolean(string='Available in POS', help='Check if you want this product to appear in the Point of Sale.', default=False)
    to_weight = fields.Boolean(string='To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration.")
    pos_categ_ids = fields.Many2many(
        'pos.category', string='Point of Sale Category',
        help="Category used in the Point of Sale.")
    public_description = fields.Html(
        string="Product Description",
        translate=True
    )

    def create_product_variant_from_pos(self, attribute_value_ids, config_id):
        """ Create a product variant from the POS interface. """
        self.ensure_one()
        product_template_attribute_value_ids = self.env['product.template.attribute.value'].browse(attribute_value_ids)
        product_variant = self._create_product_variant(product_template_attribute_value_ids)
        return {
            'product.product': product_variant.read(self.env['product.product']._load_pos_data_fields(config_id), load=False),
        }

    @api.model
    def _load_pos_data_domain(self, data):
        domain = [
            *self.env['product.template']._check_company_domain(data['pos.config'][0]['company_id']),
            ('available_in_pos', '=', True),
            ('sale_ok', '=', True),
        ]
        limited_categories = data['pos.config'][0]['limit_categories']
        if limited_categories:
            available_category_ids = data['pos.config'][0]['iface_available_categ_ids']
            category_ids = self.env['pos.category'].browse(available_category_ids)._get_descendants().ids
            domain += [('pos_categ_ids', 'in', category_ids)]
        return domain

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'display_name', 'standard_price', 'categ_id', 'pos_categ_ids', 'taxes_id', 'barcode', 'name', 'list_price', 'is_favorite',
            'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'tracking', 'type', 'service_tracking', 'is_storable',
            'write_date', 'available_in_pos', 'attribute_line_ids', 'active', 'image_128', 'combo_ids', 'product_variant_ids', 'public_description'
        ]

    def _load_pos_data(self, data):
        # Add custom fields for 'formula' taxes.
        fields = set(self._load_pos_data_fields(data['pos.config'][0]['id']))
        taxes = self.env['account.tax'].search(self.env['account.tax']._load_pos_data_domain(data))
        product_fields = taxes._eval_taxes_computation_prepare_product_fields()
        fields = list(fields.union(product_fields))

        config = self.env['pos.config'].browse(data['pos.config'][0]['id'])
        limit_count = config.get_limited_product_count()
        pos_limited_loading = self.env.context.get('pos_limited_loading', True)
        if limit_count and pos_limited_loading:
            query = self._where_calc(self._load_pos_data_domain(data))
            sql = SQL(
                """
                    WITH pm AS (
                        SELECT pp.product_tmpl_id,
                            MAX(sml.write_date) date
                        FROM stock_move_line sml
                        JOIN product_product pp ON sml.product_id = pp.id
                        GROUP BY pp.product_tmpl_id
                    )
                    SELECT product_template.id
                        FROM %s
                    LEFT JOIN pm ON product_template.id = pm.product_tmpl_id
                        WHERE %s
                    ORDER BY product_template.is_favorite DESC,
                        CASE WHEN product_template.type = 'service' THEN 1 ELSE 0 END DESC,
                        pm.date DESC NULLS LAST,
                        product_template.write_date DESC
                    LIMIT %s
                """,
                query.from_clause,
                query.where_clause or SQL("TRUE"),
                limit_count,
            )
            product_tmpl_ids = [r[0] for r in self.env.execute_query(sql)]
            products = self._load_product_with_domain([('id', 'in', product_tmpl_ids)])
            product_combo = products.filtered(lambda p: p['type'] == 'combo')
            products += product_combo.combo_ids.combo_item_ids.product_id.product_tmpl_id
        else:
            domain = self._load_pos_data_domain(data)
            products = self._load_product_with_domain(domain)

        data['pos.config'][0]['_product_default_values'] = \
            self.env['account.tax']._eval_taxes_computation_prepare_product_default_values(product_fields)

        products += config._get_special_products().product_tmpl_id
        if config.tip_product_id:
            products += config.tip_product_id.product_tmpl_id

        fields = self._load_pos_data_fields(config.id)
        available_products = products.read(fields, load=False)
        self._process_pos_ui_product_product(available_products, config)
        return available_products

    def _load_product_with_domain(self, domain, load_archived=False):
        context = {**self.env.context, 'display_default_code': False, 'active_test': not load_archived}
        domain = self._server_date_to_domain(domain)
        return self.with_context(context).search(
            domain,
            order='sequence,default_code,name')

    def _process_pos_ui_product_product(self, products, config_id):

        def filter_taxes_on_company(product_taxes, taxes_by_company):
            """
            Filter the list of tax ids on a single company starting from the current one.
            If there is no tax in the result, it's filtered on the parent company and so
            on until a non empty result is found.
            """
            taxes, comp = None, self.env.company
            while not taxes and comp:
                taxes = list(set(product_taxes) & set(taxes_by_company[comp.id]))
                comp = comp.parent_id
            return taxes

        taxes = self.env['account.tax'].search(self.env['account.tax']._check_company_domain(self.env.company))
        # group all taxes by company in a dict where:
        # - key: ID of the company
        # - values: list of tax ids
        taxes_by_company = defaultdict(set)
        if self.env.company.parent_id:
            for tax in taxes:
                taxes_by_company[tax.company_id.id].add(tax.id)

        different_currency = config_id.currency_id != self.env.company.currency_id
        for product in products:
            if different_currency:
                product['lst_price'] = self.env.company.currency_id._convert(product['lst_price'], config_id.currency_id, self.env.company, fields.Date.today())
            product['image_128'] = bool(product['image_128'])

            if len(taxes_by_company) > 1 and len(product['taxes_id']) > 1:
                product['taxes_id'] = filter_taxes_on_company(product['taxes_id'], taxes_by_company)

            product['_archived_combinations'] = []
            for product_product in self.env['product.product'].with_context(active_test=False).search([('product_tmpl_id', '=', product['id']), ('active', '=', False)]):
                product['_archived_combinations'].append(product_product.product_template_attribute_value_ids.ids)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_open_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('available_in_pos', '=', True)]):
            if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
                raise UserError(_(
                    "To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!",
                ))

    @api.onchange('sale_ok')
    def _onchange_sale_ok(self):
        if not self.sale_ok:
            self.available_in_pos = False

    @api.onchange('available_in_pos')
    def _onchange_available_in_pos(self):
        if self.available_in_pos and not self.sale_ok:
            self.sale_ok = True

    @api.constrains('available_in_pos')
    def _check_combo_inclusions(self):
        for product in self:
            if not product.available_in_pos:
                combo_name = self.env['product.combo.item'].sudo().search([('product_id', 'in', product.product_variant_ids.ids)], limit=1).combo_id.name
                if combo_name:
                    raise UserError(_('You must first remove this product from the %s combo', combo_name))

    def get_product_info_pos(self, price, quantity, pos_config_id, product_variant_id=False):
        self.ensure_one()
        config = self.env['pos.config'].browse(pos_config_id)
        product_variant = self.env['product.product'].browse(product_variant_id) if product_variant_id else False
        template_or_variant = product_variant or self

        # Tax related
        taxes = self.taxes_id.compute_all(price, config.currency_id, quantity, template_or_variant)
        grouped_taxes = {}
        for tax in taxes['taxes']:
            if tax['id'] in grouped_taxes:
                grouped_taxes[tax['id']]['amount'] += tax['amount'] / quantity if quantity else 0
            else:
                grouped_taxes[tax['id']] = {
                    'name': tax['name'],
                    'amount': tax['amount'] / quantity if quantity else 0
                }

        all_prices = {
            'price_without_tax': taxes['total_excluded'] / quantity if quantity else 0,
            'price_with_tax': taxes['total_included'] / quantity if quantity else 0,
            'tax_details': list(grouped_taxes.values()),
        }

        # Pricelists
        if config.use_pricelist:
            pricelists = config.available_pricelist_ids
        else:
            pricelists = config.pricelist_id
        price_per_pricelist_id = pricelists._price_get(template_or_variant, quantity) if pricelists else False
        pricelist_list = [{'name': pl.name, 'price': price_per_pricelist_id[pl.id]} for pl in pricelists]

        # Warehouses
        warehouse_list = [
            {'id': w.id,
            'name': w.name,
            'available_quantity': template_or_variant.with_context({'warehouse_id': w.id}).qty_available,
            'forecasted_quantity': template_or_variant.with_context({'warehouse_id': w.id}).virtual_available,
            'uom': template_or_variant.uom_name}
            for w in self.env['stock.warehouse'].search([('company_id', '=', config.company_id.id)])]

        if config.picking_type_id.warehouse_id:
            # Sort the warehouse_list, prioritizing config.picking_type_id.warehouse_id
            warehouse_list = sorted(
                warehouse_list,
                key=lambda w: w['id'] != config.picking_type_id.warehouse_id.id
            )

        # Suppliers
        key = itemgetter('partner_id')
        supplier_list = []
        for _key, group in groupby(sorted(self.seller_ids, key=key), key=key):
            for s in group:
                if not ((s.date_start and s.date_start > date.today()) or (s.date_end and s.date_end < date.today()) or (s.min_qty > quantity)):
                    supplier_list.append({
                        'name': s.partner_id.name,
                        'delay': s.delay,
                        'price': s.price
                    })
                    break

        # Variants
        variant_list = [{'name': attribute_line.attribute_id.name,
                         'values': [{'name': attr_name, 'search': f'{self.name} {attr_name}'} for attr_name in attribute_line.value_ids.mapped('name')]}
                        for attribute_line in self.attribute_line_ids]

        return {
            'all_prices': all_prices,
            'pricelists': pricelist_list,
            'warehouses': warehouse_list,
            'suppliers': supplier_list,
            'variants': variant_list
        }
