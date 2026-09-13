from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

from ..tools import debug_log as dbg


class ProductTemplatePosLoad(models.Model):
    _inherit = "product.template"
    _pos_data_incremental = True

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = [
            *self._check_company_domain(config.company_id),
            ("available_in_pos", "=", True),
            ("sale_ok", "=", True),
        ]
        if config.limit_categories:
            domain += [("pos_categ_ids", "in", config.iface_available_categ_ids.ids)]
        return domain

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "display_name",
            "standard_price",
            "categ_id",
            "pos_categ_ids",
            "taxes_id",
            "barcode",
            "name",
            "list_price",
            "is_favorite",
            "default_code",
            "to_weight",
            "uom_id",
            "description_sale",
            "description",
            "tracking",
            "type",
            "service_tracking",
            "is_storable",
            "write_date",
            "color",
            "pos_sequence",
            "available_in_pos",
            "attribute_line_ids",
            "active",
            "image_128",
            "combo_ids",
            "product_variant_ids",
            "public_description",
            "pos_optional_product_ids",
            "sequence",
            "product_tag_ids",
        ]

    @api.model
    @dbg.timed
    def _load_pos_data_search_read(self, data, config):
        domain = self._load_pos_data_domain(data, config)
        limit_count = config.get_limited_product_count()
        limited = bool(
            limit_count and self.env.context.get("pos_limited_loading", True)
        )
        dbg.pipeline.debug(
            "[load:product.template] limit=%s limited=%s domain=%s",
            limit_count,
            limited,
            domain,
        )
        if limited:
            dated_domain = self._add_server_date_to_domain(domain)
            if dated_domain is False:
                return []
            with dbg.timer(self.env, "[load:product.template] ranked ids"):
                recent_ids = self._get_ids_ranked_for_pos(dated_domain, limit_count)
            products = self._load_product_with_domain([("id", "in", recent_ids)])
        else:
            products = self._load_product_with_domain(domain)
        base_count = len(products)

        combos = products.filtered(lambda product: product.type == "combo")
        products |= combos.combo_ids.combo_item_ids.product_id.product_tmpl_id
        products |= (
            config._get_special_products()
            .filtered(
                lambda product: (
                    not product.sudo().company_id
                    or product.sudo().company_id == self.env.company
                )
            )
            .product_tmpl_id
        )
        products |= products.pos_optional_product_ids
        if data.get("pos.order.line"):
            products |= (
                self.env["product.product"]
                .browse([line["product_id"] for line in data["pos.order.line"]])
                .product_tmpl_id
            )
        dbg.logic.debug(
            "[load:product.template] %d ranked + combos(%d)/special/optional/open"
            " order lines -> %d templates",
            base_count,
            len(combos),
            len(products),
        )

        return self._load_pos_data_read(products, config)

    @api.model
    def _load_pos_data_read(self, records, config):
        records = records._with_pos_company(config)
        rows = super()._load_pos_data_read(records, config)
        with dbg.timer(self.env, "[load:product.template] currency rows"):
            self._update_rows_with_config_currency(rows, config)
        with dbg.timer(self.env, "[load:product.template] company taxes"):
            self._update_rows_with_company_taxes(rows, config)
        with dbg.timer(self.env, "[load:product.template] archived combinations"):
            self._add_archived_combinations(rows)
        for row in rows:
            row["image_128"] = bool(row["image_128"])
        return rows

    @api.model
    @dbg.timed
    def load_product_from_pos(self, config_id, domain, offset=0, limit=0):
        config = self.env["pos.config"].browse(config_id)
        config.check_access("read")
        domain = Domain(domain)
        load_archived = self.env.context.get("load_archived", False)
        product_tmpls = self._load_product_with_domain(
            domain, load_archived, offset, limit
        )
        combos = product_tmpls.filtered(lambda template: template.type == "combo")
        product_tmpls |= combos.combo_ids.combo_item_ids.product_id.product_tmpl_id
        products = product_tmpls.product_variant_ids
        dbg.pipeline.debug(
            "[load:product] on demand config=%s domain=%s offset=%s limit=%s"
            " archived=%s -> %d templates, %d variants",
            config_id,
            domain,
            offset,
            limit,
            load_archived,
            len(product_tmpls),
            len(products),
        )

        return {
            **self._get_pos_pricelist_data(product_tmpls, products, config),
            **self._get_pos_combo_data(product_tmpls, config),
            **self._get_pos_attribute_data(product_tmpls, config),
            **self._get_pos_packaging_data(products, domain, config),
            **self._get_pos_tax_data(product_tmpls, config),
            "product.product": self.env["product.product"]._load_pos_data_read(
                products.with_context(display_default_code=False), config
            ),
            "product.template": self._load_pos_data_read(product_tmpls, config),
        }

    @api.model
    def _get_ids_ranked_for_pos(self, domain, limit):
        query = self._search(domain, bypass_access=True)
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
                    product_template.write_date DESC, product_template.id
                LIMIT %s
            """,
            query.from_clause,
            query.where_clause or SQL("TRUE"),
            limit,
        )
        ids = [row[0] for row in self.env.execute_query(sql)]
        dbg.logic.debug(
            "[load:product.template] ranked query: limit=%s -> %d ids", limit, len(ids)
        )
        return ids

    def _load_product_with_domain(self, domain, load_archived=False, offset=0, limit=0):
        return self.with_context(
            display_default_code=False,
            active_test=not load_archived,
            bin_size=True,
        ).search(
            self._add_server_date_to_domain(domain),
            order="sequence,default_code,name",
            offset=offset,
            limit=limit or False,
        )

    @api.model
    def _get_pos_pricelist_data(self, product_tmpls, products, config):
        return config.get_pos_ui_product_pricelist_item_by_product(
            product_tmpls.ids, products.ids
        )

    @api.model
    def _get_pos_combo_data(self, product_tmpls, config):
        combos = product_tmpls.combo_ids
        return {
            "product.combo": self.env["product.combo"]._load_pos_data_read(
                combos, config
            ),
            "product.combo.item": self.env["product.combo.item"]._load_pos_data_read(
                combos.combo_item_ids, config
            ),
        }

    @api.model
    def _get_pos_attribute_data(self, product_tmpls, config):
        attribute_lines = product_tmpls.attribute_line_ids
        attribute_values = attribute_lines.product_template_value_ids
        exclusion = self.env["product.template.attribute.exclusion"]
        exclusions = attribute_values.exclude_for | exclusion.search(
            [("product_tmpl_id", "in", product_tmpls.ids)]
        )
        line_model = self.env["product.template.attribute.line"]
        value_model = self.env["product.template.attribute.value"]
        return {
            "product.template.attribute.line": line_model._load_pos_data_read(
                attribute_lines, config
            ),
            "product.template.attribute.value": value_model._load_pos_data_read(
                attribute_values, config
            ),
            "product.template.attribute.exclusion": exclusion._load_pos_data_read(
                exclusions, config
            ),
        }

    @api.model
    def _get_pos_packaging_data(self, products, domain, config):
        product_uom = self.env["product.uom"]
        packaging_domain = Domain(
            "product_id", "in", products.ids
        ) | self._get_domain_scanned_barcodes(domain)
        return {
            "product.uom": product_uom._load_pos_data_read(
                product_uom.search(packaging_domain), config
            ),
        }

    @api.model
    def _get_domain_scanned_barcodes(self, domain):
        conditions = [
            Domain("barcode", condition.operator, condition.value)
            for condition in domain.iter_conditions()
            if condition.field_expr.endswith("barcode")
            and condition.operator in ("=", "in")
        ]
        return Domain.OR(conditions) if conditions else Domain.FALSE

    @api.model
    def _get_pos_tax_data(self, product_tmpls, config):
        account_tax = self.env["account.tax"]
        tax_domain = Domain(
            account_tax._check_company_domain(config.company_id)
        ) & Domain("id", "in", product_tmpls.taxes_id.ids)
        return {
            "account.tax": account_tax._load_pos_data_read(
                account_tax.search(tax_domain), config
            ),
        }

    @api.model
    def _update_rows_with_config_currency(self, rows, config):
        if not rows:
            return
        company = config.company_id
        target = config.currency_id
        today = fields.Date.today()
        templates = self.browse([row["id"] for row in rows])._with_pos_company(config)
        currencies_by_id = {
            template.id: (template.currency_id, template.cost_currency_id)
            for template in templates
        }
        for row in rows:
            list_currency, cost_currency = currencies_by_id[row["id"]]
            if list_currency != target:
                row["list_price"] = list_currency._convert(
                    row["list_price"], target, company, today
                )
            if cost_currency != target:
                row["standard_price"] = cost_currency._convert(
                    row["standard_price"], target, company, today
                )

    @api.model
    def _update_rows_with_company_taxes(self, rows, config):
        company = config.company_id
        if not company.parent_id:
            return
        account_tax = self.env["account.tax"]
        taxes_by_company = self._get_taxes_by_company(
            account_tax.search(account_tax._check_company_domain(company))
        )
        if len(taxes_by_company) < 2:
            return
        dbg.logic.debug(
            "[load:product.template] branch company %s: taxes narrowed across %d"
            " companies",
            company.id,
            len(taxes_by_company),
        )
        for row in rows:
            if len(row["taxes_id"]) > 1:
                row["taxes_id"] = self._get_tax_ids_of_nearest_company(
                    row["taxes_id"], taxes_by_company, company
                )

    @api.model
    def _get_taxes_by_company(self, taxes):
        taxes_by_company = {}
        for tax in taxes:
            for company_id in tax.sudo().company_ids.ids:
                taxes_by_company.setdefault(company_id, set()).add(tax.id)
        return taxes_by_company

    @api.model
    def _get_tax_ids_of_nearest_company(self, tax_ids, taxes_by_company, company):
        matching = []
        while not matching and company:
            owned = taxes_by_company.get(company.id, frozenset())
            matching = [tax_id for tax_id in tax_ids if tax_id in owned]
            company = company.sudo().parent_id
        return matching

    def _add_archived_combinations(self, products):
        product_data = {product["id"]: product for product in products}
        for product_tmpl in self.browse(product_data.keys()):
            product = product_data[product_tmpl.id]
            if not product_tmpl.attribute_line_ids:
                product["_archived_combinations"] = []
                continue
            combinations = product_tmpl._get_archived_combinations()
            exclusions = product_tmpl._complete_inverse_exclusions(
                product_tmpl._get_own_attribute_exclusions()
            )
            for ptav_id, ptav_ids in exclusions.items():
                combinations.extend((ptav_id, other) for other in ptav_ids)
            product["_archived_combinations"] = combinations
