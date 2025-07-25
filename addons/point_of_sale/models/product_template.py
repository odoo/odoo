# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import SQL
from itertools import groupby
from operator import itemgetter
from datetime import date
from odoo.osv import expression
from odoo.fields import Domain


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
    color = fields.Integer('Color Index', compute="_compute_color", store=True, readonly=False)

    @api.depends('pos_categ_ids')
    def _compute_color(self):
        """Automatically set the color field based on the selected category."""
        for product in self:
            if product.pos_categ_ids:
                product.color = product.pos_categ_ids[0].color

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
    def load_product_from_pos(self, config_id, domain, offset=0, limit=0):
        load_archived = self.env.context.get('load_archived', False)
        domain_obj = Domain(domain)
        config = self.env['pos.config'].browse(config_id)
        product_tmpls = self._load_product_with_domain(domain_obj, load_archived, offset, limit)

        # product.combo and product.combo.item loading
        for product_tmpl in product_tmpls:
            if product_tmpl.type == 'combo':
                product_tmpls += product_tmpl.combo_ids.combo_item_ids.product_id.product_tmpl_id

        combo_domain = [('id', 'in', product_tmpls.combo_ids.ids)]
        combo_fields = self.env['product.combo']._load_pos_data_fields(config.id)
        combo_read = self.env['product.combo'].search_read(combo_domain, combo_fields, load=False)
        combo_item_domain = [('combo_id', 'in', product_tmpls.combo_ids.ids)]
        combo_item_fields = self.env['product.combo.item']._load_pos_data_fields(config.id)
        combo_item_read = self.env['product.combo.item'].search_read(combo_item_domain, combo_item_fields, load=False)

        products = product_tmpls.product_variant_ids

        # product.pricelist_item & product.pricelist loading
        pricelists = config.current_session_id.get_pos_ui_product_pricelist_item_by_product(
            product_tmpls.ids,
            products.ids,
            config.id
        )

        # product.template.attribute.value & product.template.attribute.line loading
        product_tmpl_attr_line = product_tmpls.attribute_line_ids
        product_tmpl_attr_value = product_tmpls.attribute_line_ids.product_template_value_ids
        product_tmpl_attr_value_fields = product_tmpl_attr_value._load_pos_data_fields(config.id)
        product_tmpl_attr_line_fields = product_tmpl_attr_line._load_pos_data_fields(config.id)
        product_tmpl_attr_value_read = product_tmpl_attr_value.read(product_tmpl_attr_value_fields, load=False)
        product_tmpl_attr_line_read = product_tmpl_attr_line.read(product_tmpl_attr_line_fields, load=False)

        # product.template.attribute.exclusion loading
        product_tmpl_excl = self.env['product.template.attribute.exclusion']
        product_tmpl_exclusion = product_tmpl_attr_value.exclude_for + product_tmpl_excl.search([
            ('product_tmpl_id', 'in', product_tmpls.ids),
        ])
        product_tmpl_exclusion_fields = product_tmpl_exclusion._load_pos_data_fields(config.id)
        product_tmpl_exclusion_read = product_tmpl_exclusion.read(product_tmpl_exclusion_fields, load=False)

        # product.product loading
        product_fields = products._load_pos_data_fields(config.id)
        product_read = products.with_context(display_default_code=False).read(product_fields, load=False)

        # product.template loading
        product_tmpl_fields = self._load_pos_data_fields(config.id)
        product_tmpl_read = product_tmpls.read(product_tmpl_fields, load=False)

        # product.uom loading
        packaging_domain = Domain([('product_id', 'in', products.ids)])
        conditions = list(domain_obj.iter_conditions())
        barcode_in_domain = any('barcode' in condition.field_expr for condition in conditions)

        if barcode_in_domain:
            barcode = [condition.value for condition in conditions if 'barcode' in condition.field_expr]
            flat = [item for sublist in barcode for item in sublist]
            packaging_domain = expression.OR([packaging_domain, [('barcode', 'in', flat)]])

        packaging_fields = self.env['product.uom']._load_pos_data_fields(config.id)
        packaging = self.env['product.uom'].search(packaging_domain)
        condition = packaging and packaging.product_id

        # account.tax loading
        tax_domain = self.env['account.tax']._check_company_domain(config.company_id.id)
        tax_domain = expression.AND([tax_domain, [['id', 'in', product_tmpls.taxes_id.ids]]])
        tax_fields = self.env['account.tax']._load_pos_data_fields(config.id)
        tax_read = self.env['account.tax'].search_read(tax_domain, tax_fields, load=False)

        return {
            **pricelists,
            'account.tax': tax_read,
            'product.product': products.with_context(config_id=config_id)._post_read_pos_data(product_read),
            'product.template': self.with_context(config_id=config.id)._post_read_pos_data(product_tmpl_read),
            'product.uom': packaging.read(packaging_fields, load=False) if condition else [],
            'product.combo': combo_read,
            'product.combo.item': combo_item_read,
            'product.template.attribute.value': product_tmpl_attr_value_read,
            'product.template.attribute.line': product_tmpl_attr_line_read,
            'product.template.attribute.exclusion': product_tmpl_exclusion_read,
        }

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'display_name', 'standard_price', 'categ_id', 'pos_categ_ids', 'taxes_id', 'barcode', 'name', 'list_price', 'is_favorite',
            'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'tracking', 'type', 'service_tracking', 'is_storable',
            'write_date', 'color', 'available_in_pos', 'attribute_line_ids', 'active', 'image_128', 'combo_ids', 'product_variant_ids',
            'public_description', 'sequence',
        ]

    def _load_pos_data(self, data):
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
                    ORDER BY product_template.is_favorite DESC NULLS LAST,
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
        else:
            domain = self._load_pos_data_domain(data)
            products = self._load_product_with_domain(domain)

        product_combo = products.filtered(lambda p: p['type'] == 'combo')
        products += product_combo.combo_ids.combo_item_ids.product_id.product_tmpl_id

        special_products = config._get_special_products().filtered(
                    lambda product: not product.sudo().company_id
                                    or product.sudo().company_id == self.company_id
                )
        products += special_products.product_tmpl_id
        if config.tip_product_id:
            tip_company_id = config.tip_product_id.sudo().company_id
            if not tip_company_id or tip_company_id == self.env.company:
                products += config.tip_product_id.product_tmpl_id

        fields = self._load_pos_data_fields(config.id)
        return self.with_context(config_id=config.id)._post_read_pos_data(products.read(fields, load=False))

    def _post_read_pos_data(self, data):
        config = self.env['pos.config'].browse(self.env.context.get('config_id'))
        self._process_pos_ui_product_product(data, config)
        return super()._post_read_pos_data(data)

    def _load_product_with_domain(self, domain, load_archived=False, offset=0, limit=0):
        context = {**self.env.context, 'display_default_code': False, 'active_test': not load_archived}
        domain = self._server_date_to_domain(domain)
        return self.with_context(context).search(
            domain,
            order='sequence,default_code,name',
            offset=offset,
            limit=limit if limit else False
        )

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

        self._add_archived_combinations(products)
        for product in products:
            if different_currency:
                product['list_price'] = self.env.company.currency_id._convert(product['list_price'], config_id.currency_id, self.env.company, fields.Date.today())
                product['standard_price'] = self.env.company.currency_id._convert(product['standard_price'], config_id.currency_id, self.env.company, fields.Date.today())

            product['image_128'] = bool(product['image_128'])

            if len(taxes_by_company) > 1 and len(product['taxes_id']) > 1:
                product['taxes_id'] = filter_taxes_on_company(product['taxes_id'], taxes_by_company)

    def _add_archived_combinations(self, products):
        """ Add archived combinations to the product template data. """
        product_data = {product['id']: product for product in products}
        for product_tmpl in self.browse(product_data.keys()):
            product = product_data[product_tmpl.id]
            attribute_exclusions = product_tmpl._get_attribute_exclusions()
            product['_archived_combinations'] = attribute_exclusions['archived_combinations']
            excluded = {}
            for ptav_id, ptav_ids in attribute_exclusions['exclusions'].items():
                for ptav_id2 in set(ptav_ids) - excluded.keys():
                    excluded[ptav_id] = ptav_id2
            product['_archived_combinations'].extend(excluded.items())

    @api.ondelete(at_uninstall=False)
    def _unlink_except_open_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('available_in_pos', '=', True)]):
            if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
                raise UserError(_(
                    "To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!",
                ))

    def _ensure_unused_in_pos(self):
        open_pos_sessions = self.env['pos.session'].search([('state', '!=', 'closed')])
        used_products = open_pos_sessions.order_ids.filtered(lambda o: o.state == "draft").lines.product_id.product_tmpl_id
        if used_products & self:
            raise UserError(_(
                "Hold up! Archiving products while POS sessions are active is like pulling a plate mid-meal.\n"
                "Make sure to close all sessions first to avoid any issues.",
            ))

    def action_archive(self):
        self._ensure_unused_in_pos()
        return super().action_archive()

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
        tax_to_use = self.env['account.tax']
        company = config.company_id
        while not tax_to_use and company:
            tax_to_use = self.taxes_id.filtered(lambda tax: tax.company_id.id == company.id)
            if not tax_to_use:
                company = company.parent_id
        taxes = tax_to_use.compute_all(price, config.currency_id, quantity, self)
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
                        'id': s.id,
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
