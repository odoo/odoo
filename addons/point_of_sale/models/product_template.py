# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import SQL, is_html_empty
from itertools import groupby
from operator import itemgetter
from datetime import date
from odoo.fields import Domain


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'pos.load.mixin']

    @api.model
    def _default_pos_sequence(self):
        self.env.cr.execute('SELECT MAX(pos_sequence) FROM %s' % self._table)
        max_sequence = self.env.cr.fetchone()[0]
        if max_sequence is None:
            return 1
        return max_sequence + 1

    available_in_pos = fields.Boolean(string='Available in POS', help='Check if you want this product to appear in the Point of Sale.', default=False)
    to_weight = fields.Boolean(string='To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration.")
    pos_categ_ids = fields.Many2many(
        'pos.category', string='Point of Sale Category',
        help="Category used in the Point of Sale.")
    public_description = fields.Html(
        string="Product Description",
        translate=True
    )
    pos_optional_product_ids = fields.Many2many(
        comodel_name='product.template',
        relation='pos_product_optional_rel',
        column1='src_id',
        column2='dest_id',
        string="POS Optional Products",
        help="Optional products are suggested when customers add items to their cart (e.g., adding a burger suggests cold drinks or fries).")
    color = fields.Integer('Color Index', compute="_compute_color", store=True, readonly=False)
    pos_sequence = fields.Integer(
        string="POS Sequence",
        help="Determine the display order in the POS Terminal",
        default=_default_pos_sequence,
        copy=False,
    )

    def write(self, vals):
        # Clear empty public description content to avoid side-effects on product page
        # when there is no content to display anyway.
        if vals.get('public_description') and is_html_empty(vals['public_description']):
            vals['public_description'] = ''
        return super().write(vals)

    @api.depends('pos_categ_ids')
    def _compute_color(self):
        """Automatically set the color field based on the selected category."""
        for product in self:
            if product.pos_categ_ids:
                product.color = product.pos_categ_ids[0].color

    def create_product_variant_from_pos(self, attribute_value_ids, config_id):
        """ Create a product variant from the POS interface. """
        self.ensure_one()
        pos_config = self.env['pos.config'].browse(config_id)
        product_template_attribute_value_ids = self.env['product.template.attribute.value'].browse(attribute_value_ids)
        product_variant = self._create_product_variant(product_template_attribute_value_ids)
        return {
            'product.product': product_variant.read(self.env['product.product']._load_pos_data_fields(pos_config), load=False),
        }

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = [
            *self.env['product.template']._check_company_domain(config.company_id),
            ('available_in_pos', '=', True),
            ('sale_ok', '=', True),
        ]
        if config.limit_categories:
            domain += [('pos_categ_ids', 'in', config.iface_available_categ_ids.ids)]
        return domain

    @api.model
    def load_product_from_pos(self, config_id, domain, offset=0, limit=0):
        load_archived = self.env.context.get('load_archived', False)
        domain = Domain(domain)
        config = self.env['pos.config'].browse(config_id)
        product_tmpls = self._load_product_with_domain(domain, load_archived, offset, limit)

        # product.combo and product.combo.item loading
        for product_tmpl in product_tmpls:
            if product_tmpl.type == 'combo':
                product_tmpls += product_tmpl.combo_ids.combo_item_ids.product_id.product_tmpl_id

        combo_domain = Domain('id', 'in', product_tmpls.combo_ids.ids)
        combo_records = self.env['product.combo'].search(combo_domain)
        combo_read = self.env['product.combo']._load_pos_data_read(combo_records, config)
        combo_item_domain = Domain('combo_id', 'in', product_tmpls.combo_ids.ids)
        combo_item_records = self.env['product.combo.item'].search(combo_item_domain)
        combo_item_read = self.env['product.combo.item']._load_pos_data_read(combo_item_records, config)

        products = product_tmpls.product_variant_ids

        # product.pricelist_item & product.pricelist loading
        pricelists = config.current_session_id.get_pos_ui_product_pricelist_item_by_product(
            product_tmpls.ids,
            products.ids,
            config.id
        )

        # product.template.attribute.value & product.template.attribute.line loading
        product_tmpl_attr_line = product_tmpls.attribute_line_ids
        product_tmpl_attr_line_read = product_tmpl_attr_line._load_pos_data_read(product_tmpl_attr_line, config)
        product_tmpl_attr_value = product_tmpls.attribute_line_ids.product_template_value_ids
        product_tmpl_attr_value_read = product_tmpl_attr_value._load_pos_data_read(product_tmpl_attr_value, config)

        # product.template.attribute.exclusion loading
        product_tmpl_excl = self.env['product.template.attribute.exclusion']
        product_tmpl_exclusion = product_tmpl_attr_value.exclude_for + product_tmpl_excl.search([
            ('product_tmpl_id', 'in', product_tmpls.ids),
        ])
        product_tmpl_exclusion_read = product_tmpl_excl._load_pos_data_read(product_tmpl_exclusion, config)

        # product.product loading
        product_read = products._load_pos_data_read(products.with_context(display_default_code=False), config)

        # product.template loading
        product_tmpl_read = self._load_pos_data_read(product_tmpls, config)

        # product.uom loading
        packaging_domain = Domain('product_id', 'in', products.ids)
        barcode_in_domain = any('barcode' in condition.field_expr for condition in domain.iter_conditions())

        if barcode_in_domain:
            barcode = [condition.value for condition in domain.iter_conditions() if 'barcode' in condition.field_expr]
            flat = [item for sublist in barcode for item in sublist]
            packaging_domain |= Domain('barcode', 'in', flat)

        product_uom = self.env['product.uom']
        packaging = product_uom.search(packaging_domain)
        condition = packaging and packaging.product_id
        packaging_read = product_uom._load_pos_data_read(packaging, config) if condition else []

        # account.tax loading
        account_tax = self.env['account.tax']
        tax_domain = Domain(account_tax._check_company_domain(config.company_id.id))
        tax_domain &= Domain('id', 'in', product_tmpls.taxes_id.ids)
        tax_read = account_tax._load_pos_data_read(account_tax.search(tax_domain), config)

        return {
            **pricelists,
            'account.tax': tax_read,
            'product.product': product_read,
            'product.template': product_tmpl_read,
            'product.uom': packaging_read,
            'product.combo': combo_read,
            'product.combo.item': combo_item_read,
            'product.template.attribute.value': product_tmpl_attr_value_read,
            'product.template.attribute.line': product_tmpl_attr_line_read,
            'product.template.attribute.exclusion': product_tmpl_exclusion_read,
        }

    @api.model
    def _load_pos_data_fields_to_exclude(self, config, record_count):
        """Skip slow M2M/O2M fields when bulk-loading templates.

        These are fetched via direct SQL in _process_pos_ui_data instead.
        """
        if record_count > 1000:
            return [
                'all_product_tag_ids', 'product_tag_ids', 'pos_categ_ids',
                'taxes_id', 'combo_ids', 'pos_optional_product_ids',
                'product_variant_ids', 'standard_price', 'barcode',
            ]
        return []

    @api.model
    def _process_pos_ui_data(self, records, config):
        """Batch-simulate template fields that were excluded from the ORM read.

        Uses direct SQL to fetch M2M relations and O2M variants in bulk,
        avoiding N+1 queries on large catalogs.
        """
        super()._process_pos_ui_data(records, config)

        # SQL batch simulation only needed when fields were excluded (large loads)
        if len(records) > 1000:
            self._batch_simulate_template_fields(records)

        # These MUST always run regardless of batch size
        self._add_archived_combinations(records)
        self._apply_product_processing(records, config)

    @api.model
    def _batch_simulate_template_fields(self, records):
        """Fetch excluded M2M/O2M fields via direct SQL for large catalogs."""
        tmpl_ids = [r['id'] for r in records]
        tmpl_id_tuple = tuple(tmpl_ids)

        # --- Batch fetch M2M relations via SQL ---
        pos_categs = self._batch_fetch_m2m(
            'pos_category_product_template_rel', 'product_template_id', 'pos_category_id', tmpl_id_tuple)
        taxes = self._batch_fetch_m2m(
            'product_taxes_rel', 'prod_id', 'tax_id', tmpl_id_tuple)
        tags = self._batch_fetch_m2m(
            'product_tag_product_template_rel', 'product_template_id', 'product_tag_id', tmpl_id_tuple)
        optional = self._batch_fetch_m2m(
            'pos_product_optional_rel', 'src_id', 'dest_id', tmpl_id_tuple)

        # --- Batch fetch O2M attribute lines ---
        self.env.cr.execute(
            "SELECT product_tmpl_id, id FROM product_template_attribute_line WHERE product_tmpl_id IN %s",
            [tmpl_id_tuple])
        attr_lines = defaultdict(list)
        for tid, alid in self.env.cr.fetchall():
            attr_lines[tid].append(alid)

        # --- Batch fetch O2M variants + barcodes ---
        self.env.cr.execute(
            "SELECT product_tmpl_id, id, barcode FROM product_product WHERE product_tmpl_id IN %s",
            [tmpl_id_tuple])
        variants = defaultdict(list)
        variant_barcodes = {}
        for tid, vid, bcode in self.env.cr.fetchall():
            variants[tid].append(vid)
            if bcode:
                variant_barcodes[vid] = bcode

        # --- Assign fetched data to each record ---
        for record in records:
            tid = record['id']
            record['pos_categ_ids'] = pos_categs.get(tid, [])
            record['taxes_id'] = taxes.get(tid, [])
            record['product_tag_ids'] = tags.get(tid, [])
            record['pos_optional_product_ids'] = optional.get(tid, [])
            record['combo_ids'] = []
            record['attribute_line_ids'] = attr_lines.get(tid, [])
            record['product_variant_ids'] = variants.get(tid, [])
            record['barcode'] = next(
                (variant_barcodes[vid] for vid in record['product_variant_ids'] if vid in variant_barcodes),
                False)
            if 'standard_price' not in record:
                record['standard_price'] = 0.0


    @api.model
    def _batch_fetch_m2m(self, table, src_col, dest_col, id_tuple):
        """Fetch a many2many relation in a single SQL query.

        Returns a dict mapping source IDs to lists of destination IDs.
        """
        self.env.cr.execute(
            f"SELECT {src_col}, {dest_col} FROM {table} WHERE {src_col} IN %s",
            [id_tuple])
        result = defaultdict(list)
        for src_id, dest_id in self.env.cr.fetchall():
            result[src_id].append(dest_id)
        return result

    @api.model
    def _apply_product_processing(self, records, config):
        """Shared processing for product templates and variants.

        - Currency conversion when PoS currency differs from company currency
        - Search string pre-computation
        - Tax filtering by company hierarchy
        """
        different_currency = config.currency_id != self.env.company.currency_id

        taxes_by_company = defaultdict(set)
        taxes = self.env['account.tax'].search(
            self.env['account.tax']._check_company_domain(self.env.company))
        for tax in taxes:
            taxes_by_company[tax.company_id.id].add(tax.id)

        if different_currency:
            today = fields.Date.today()
            currency = self.env.company.currency_id
            rate = currency._get_conversion_rate(currency, config.currency_id, self.env.company, today)

        company_hierarchy = []
        curr_company = self.env.company
        while curr_company:
            company_hierarchy.append(curr_company.id)
            curr_company = curr_company.parent_id

        for record in records:
            if different_currency:
                for price_field in ['list_price', 'lst_price', 'standard_price']:
                    if price_field in record:
                        record[price_field] = config.currency_id.round(record[price_field] * rate)

            # Pre-compute search string for fast client-side filtering
            name = record.get('display_name') or record.get('name') or ''
            search_parts = [name, record.get('default_code'), record.get('barcode')]
            record['search_string'] = " ".join(filter(None, search_parts)).lower() + "\n"

            # Filter taxes: keep only the most specific company's taxes
            if len(taxes_by_company) > 1 and 'taxes_id' in record and len(record['taxes_id']) > 1:
                for comp_id in company_hierarchy:
                    filtered = [tid for tid in record['taxes_id'] if tid in taxes_by_company[comp_id]]
                    if filtered:
                        record['taxes_id'] = filtered
                        break

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'display_name', 'standard_price', 'categ_id', 'pos_categ_ids', 'taxes_id', 'barcode', 'name', 'list_price', 'is_favorite',
            'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'tracking', 'type', 'service_tracking', 'is_storable',
            'write_date', 'color', 'pos_sequence', 'available_in_pos', 'attribute_line_ids', 'active', 'image_128', 'combo_ids', 'product_variant_ids', 'public_description',
            'pos_optional_product_ids', 'sequence', 'product_tag_ids'
        ]

    @api.model
    def _load_pos_data_search_read(self, data, config):
        limit_count = config.get_limited_product_count()
        pos_limited_loading = self.env.context.get('pos_limited_loading', True)
        if limit_count and pos_limited_loading:
            query = self._search(self._load_pos_data_domain(data, config), bypass_access=True)
            sql = SQL(
                """
                    SELECT product_template.id
                        FROM %(from_clause)s
                    LEFT JOIN (
                        SELECT pp.product_tmpl_id,
                            MAX(sml.write_date) date
                        FROM stock_move_line sml
                        JOIN product_product pp ON sml.product_id = pp.id
                        WHERE pp.product_tmpl_id IN (SELECT id FROM %(from_clause)s WHERE %(where_clause)s)
                        GROUP BY pp.product_tmpl_id
                    ) pm ON product_template.id = pm.product_tmpl_id
                        WHERE %(where_clause)s
                    ORDER BY product_template.is_favorite DESC NULLS LAST,
                        CASE WHEN product_template.type = 'service' THEN 1 ELSE 0 END DESC,
                        pm.date DESC NULLS LAST,
                        product_template.write_date DESC
                    LIMIT %(limit)s
                """,
                from_clause=query.from_clause,
                where_clause=query.where_clause or SQL("TRUE"),
                limit=limit_count,
            )
            product_tmpl_ids = [r[0] for r in self.env.execute_query(sql)]
            products = self._load_product_with_domain([('id', 'in', product_tmpl_ids)])
        else:
            domain = self._load_pos_data_domain(data, config)
            products = self._load_product_with_domain(domain)

        product_combo = products.filtered(lambda p: p['type'] == 'combo')
        additional_products = product_combo.combo_ids.combo_item_ids.product_id.product_tmpl_id

        special_products = config._get_special_products().filtered(
                    lambda product: not product.sudo().company_id
                                    or product.sudo().company_id == self.env.company
                )
        additional_products |= special_products.product_tmpl_id

        if config.tip_product_id:
            tip_company_id = config.tip_product_id.sudo().company_id
            if not tip_company_id or tip_company_id == self.env.company:
                additional_products |= config.tip_product_id.product_tmpl_id

        # Ensure optional products are loaded when configured.
        optional_products = products.filtered(lambda p: p.pos_optional_product_ids).pos_optional_product_ids
        additional_products |= optional_products

        # Ensure products from loaded orders are loaded
        if data.get('pos.order.line'):
            order_products = self.env['product.product'].browse([l['product_id'] for l in data['pos.order.line']]).product_tmpl_id
            additional_products |= order_products

        products |= additional_products

        return self._load_pos_data_read(products, config)


    def _load_product_with_domain(self, domain, load_archived=False, offset=0, limit=0):
        context = {**self.env.context, 'display_default_code': False, 'active_test': not load_archived, 'bin_size': True}
        domain = self._server_date_to_domain(domain)
        return self.with_context(context).search(
            domain,
            order='sequence,default_code,name',
            offset=offset,
            limit=limit if limit else False
        )


    def _add_archived_combinations(self, products):
        """ Add archived combinations to the product template data in batch. """
        product_ids = [p['id'] for p in products]
        templates = self.browse(product_ids)
        
        # Only templates with attributes can have archived combinations
        templates_with_attr = templates.filtered('attribute_line_ids')
        if not templates_with_attr:
            for p in products:
                p['_archived_combinations'] = []
            return

        # Map products by ID for easy access
        product_map = {p['id']: p for p in products}
        for p in products:
            p['_archived_combinations'] = []

        # Batch fetch variants (active and archived) for relevant templates
        all_variants = self.env['product.product'].with_context(active_test=False).search([
            ('product_tmpl_id', 'in', templates_with_attr.ids)
        ])
        
        variants_by_tmpl = defaultdict(lambda: {'active': set(), 'archived': set()})
        for v in all_variants:
            combination = tuple(sorted(v.product_template_attribute_value_ids.ids))
            if v.active:
                variants_by_tmpl[v.product_tmpl_id.id]['active'].add(combination)
            else:
                variants_by_tmpl[v.product_tmpl_id.id]['archived'].add(combination)

        for tmpl_id, counts in variants_by_tmpl.items():
            archived_only = counts['archived'] - counts['active']
            if archived_only and tmpl_id in product_map:
                product_map[tmpl_id]['_archived_combinations'] = [list(c) for c in archived_only]

        # Add exclusions from product.template.attribute.exclusion
        # These are already loaded in JS, but PoS expects them in _archived_combinations too for some logic
        exclusions = self.env['product.template.attribute.exclusion'].search([
            ('product_tmpl_id', 'in', templates_with_attr.ids)
        ])
        for excl in exclusions:
            tmpl_id = excl.product_tmpl_id.id
            if tmpl_id in product_map:
                ptav_id = excl.product_template_attribute_value_id.id
                for val in excl.value_ids:
                    product_map[tmpl_id]['_archived_combinations'].append([ptav_id, val.id])

    @api.ondelete(at_uninstall=False)
    def _unlink_except_open_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('available_in_pos', '=', True)]):
            if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
                raise UserError(_(
                    "To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!",
                ))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_special_product(self):
        self._check_is_special_product()

    def _ensure_unused_in_pos(self):
        if any(self.mapped('available_in_pos')) and self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
            raise UserError(_(
                "Hold up! Archiving products while POS sessions are active is like pulling a plate mid-meal.\n"
                "Make sure to close all sessions first to avoid any issues.",
            ))

    def _check_is_special_product(self):
        special_products = self.env['pos.config'].sudo()._get_special_products().product_tmpl_id
        for product in self:
            if product in special_products:
                raise UserError(_("You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."))

    def action_archive(self):
        self._ensure_unused_in_pos()
        self._check_is_special_product()
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
        template_or_variant = product_variant or self.product_variant_id

        # Tax related
        tax_to_use = self.env['account.tax']
        company = config.company_id
        while not tax_to_use and company:
            tax_to_use = self.taxes_id.filtered(lambda tax: tax.company_id.id == company.id)
            if not tax_to_use:
                company = company.sudo().parent_id
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
            'free_qty': template_or_variant.with_context({'warehouse_id': w.id}).free_qty,
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
            'variants': variant_list,
            'optional_products': self.pos_optional_product_ids.read(['id', 'name', 'list_price']),
        }
