from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class ProductPricelist(models.Model):
    _name = "product.pricelist"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _description = "Pricelist"
    _rec_names_search = ["name", "currency_id"]
    _order = "sequence, id, name"

    name = fields.Char(
        string="Pricelist Name",
        translate=True,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the pricelist without removing it.",
    )
    sequence = fields.Integer(default=16)

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        tracking=5,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self._default_currency_id(),
        required=True,
        tracking=1,
    )
    country_group_ids = fields.Many2many(
        comodel_name="res.country.group",
        relation="res_country_group_pricelist_rel",
        column1="pricelist_id",
        column2="res_country_group_id",
        string="Country Groups",
        tracking=10,
    )
    item_ids = fields.One2many(
        comodel_name="product.pricelist.item",
        inverse_name="pricelist_id",
        string="Pricelist Rules",
        copy=True,
        domain=lambda self: self._domain_item_ids(),
    )

    def write(self, vals):
        res = super().write(vals)

        if "company_id" in vals:
            self.env["product.pricelist.item"].search(
                [("pricelist_id", "in", self.ids)]
            )._check_company()

        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for pricelist, vals in zip(self, vals_list, strict=True):
                if vals is None:
                    continue
                vals["name"] = _("%s (copy)", pricelist.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    @api.depends("currency_id")
    def _compute_display_name(self):
        for pricelist in self:
            pricelist_name = pricelist.name or _("New")
            pricelist.display_name = f"{pricelist_name} ({pricelist.currency_id.name})"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_as_rule_base(self):
        linked_items = (
            self.env["product.pricelist.item"]
            .sudo()
            .search(
                [
                    ("base", "=", "pricelist"),
                    ("base_pricelist_id", "in", self.ids),
                    ("pricelist_id", "not in", self.ids),
                ]
            )
        )
        if linked_items:
            raise UserError(
                _(
                    "You cannot delete pricelist(s):\n(%(pricelists)s)\nThey are used within pricelist(s):\n%(other_pricelists)s",
                    pricelists="\n".join(
                        linked_items.base_pricelist_id.mapped("display_name")
                    ),
                    other_pricelists="\n".join(
                        linked_items.pricelist_id.mapped("display_name")
                    ),
                )
            )

    @api.readonly
    def action_view_pricelist_report(self):
        self.check_singleton()
        return {
            "name": _("Pricelist Report Preview"),
            "type": "ir.actions.client",
            "tag": "generate_pricelist_report",
        }

    def _get_domain_item_ids_base(self):
        return [
            "|",
            ("product_tmpl_id", "=", None),
            ("product_tmpl_id.active", "=", True),
            "|",
            ("product_id", "=", None),
            ("product_id.active", "=", True),
        ]

    def _get_price_rule(
        self,
        products,
        quantity,
        *,
        currency=None,
        uom=None,
        date=False,
        compute_price=True,
        **kwargs,
    ):
        self and self.check_singleton()

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.check_singleton()

        if not products:
            return {}

        if not date:
            date = fields.Datetime.now()

        rules = self._get_applicable_rules(products, date, **kwargs)
        rules_index = self._index_rules_by_target(rules)

        rule_by_pid = {}
        target_uom_by_pid = {}
        for product in products:
            product_uom_id = product.uom_id
            target_uom = uom or product_uom_id

            if target_uom != product_uom_id:
                qty_in_product_uom = target_uom._get_quantity_estimate(
                    quantity, product_uom_id, round=False
                )
            else:
                qty_in_product_uom = quantity

            target_uom_by_pid[product.id] = target_uom
            rule_by_pid[product.id] = self._get_suitable_rule(
                self._candidate_rules(rules, rules_index, product),
                product,
                qty_in_product_uom,
            )

        base_price_by_pid = {}
        if compute_price:
            base_price_by_pid = self._get_chained_base_prices(
                products, rule_by_pid, quantity, uom, date, currency, **kwargs
            )

        results = {}
        for product in products:
            suitable_rule = rule_by_pid[product.id]

            if compute_price:
                price = suitable_rule._get_price(
                    product,
                    quantity,
                    target_uom_by_pid[product.id],
                    date=date,
                    currency=currency,
                    base_price=base_price_by_pid.get(product.id),
                    **kwargs,
                )
            else:
                price = 0.0

            results[product.id] = (price, suitable_rule.id)

        return results

    def _get_price_rule_multi(
        self, products, quantity, uom=None, date=False, **kwargs
    ):
        if not self.ids:
            pricelists = self.search([])
        else:
            pricelists = self
        results = {}
        for pricelist in pricelists:
            subres = pricelist._get_price_rule(
                products, quantity, uom=uom, date=date, **kwargs
            )
            for product_id, price_rule in subres.items():
                results.setdefault(product_id, {})[pricelist.id] = price_rule
        return results

    def _default_currency_id(self):
        return self.env.company.currency_id.id

    def _domain_item_ids(self):
        return self._get_domain_item_ids_base()

    def _get_suitable_rule(self, rules, product, qty_in_product_uom):
        for rule in rules:
            if rule._is_applicable_for(product, qty_in_product_uom):
                return rule
        return self.env["product.pricelist.item"]

    def _index_rules_by_target(self, rules):
        index = {
            "variant": {},
            "template": {},
            "category": {},
            "global": [],
            "position": {},
        }
        for position, rule in enumerate(rules):
            index["position"][rule.id] = position
            applied_on = rule.applied_on
            if applied_on == "0_product_variant":
                index["variant"].setdefault(rule.product_id.id, []).append(rule.id)
            elif applied_on == "1_product":
                index["template"].setdefault(rule.product_tmpl_id.id, []).append(
                    rule.id
                )
            elif applied_on == "2_product_category":
                index["category"].setdefault(rule.categ_id.id, []).append(rule.id)
            else:
                index["global"].append(rule.id)
        return index

    def _candidate_rules(self, rules, index, product):
        if product._name == "product.template":
            template_id = product.id
            variant_id = (
                product.product_variant_id.id
                if product.product_variant_count == 1
                else None
            )
        else:
            template_id = product.product_tmpl_id.id
            variant_id = product.id

        rule_ids = list(index["global"])
        if variant_id:
            rule_ids += index["variant"].get(variant_id, ())
        rule_ids += index["template"].get(template_id, ())

        if index["category"]:
            category = product.categ_id
            if not category:
                ancestor_ids = ()
            elif category.parent_path:
                ancestor_ids = [
                    int(ancestor) for ancestor in category.parent_path.split("/")[:-1]
                ]
            else:
                ancestor_ids = list(index["category"])
            for ancestor_id in ancestor_ids:
                rule_ids += index["category"].get(ancestor_id, ())

        rule_ids.sort(key=index["position"].__getitem__)
        return rules.browse(rule_ids).with_prefetch(rules._prefetch_ids)

    def _get_chained_base_prices(
        self, products, rule_by_pid, quantity, uom, date, currency, **kwargs
    ):
        products_by_base_pricelist = defaultdict(lambda: self.env[products._name])
        for product in products:
            rule = rule_by_pid[product.id]
            if (
                rule.base == "pricelist"
                and rule.base_pricelist_id
                and rule.compute_price != "fixed"
            ):
                products_by_base_pricelist[rule.base_pricelist_id] |= product

        base_price_by_pid = {}
        for base_pricelist, base_products in products_by_base_pricelist.items():
            src_currency = base_pricelist.currency_id
            price_rule = base_pricelist._get_price_rule(
                base_products,
                quantity,
                currency=src_currency,
                uom=uom,
                date=date,
                **kwargs,
            )
            for product in base_products:
                price = price_rule[product.id][0]
                if src_currency != currency:
                    price = src_currency._convert(
                        price, currency, self.env.company, date, round=False
                    )
                base_price_by_pid[product.id] = price
        return base_price_by_pid

    def _get_applicable_rules(self, products, date, **kwargs):
        self and self.check_singleton()
        if not self:
            return self.env["product.pricelist.item"]

        return self.env["product.pricelist.item"].search(
            self._get_domain_applicable_rules(products=products, date=date, **kwargs)
        )

    def _get_domain_applicable_rules(self, products, date, **kwargs):
        self and self.check_singleton()
        if products._name == "product.template":
            templates_domain = ("product_tmpl_id", "in", products.ids)
            products_domain = ("product_id.product_tmpl_id", "in", products.ids)
        else:
            templates_domain = ("product_tmpl_id", "in", products.product_tmpl_id.ids)
            products_domain = ("product_id", "in", products.ids)

        return [
            ("pricelist_id", "=", self.id),
            "|",
            ("categ_id", "=", False),
            ("categ_id", "parent_of", products.categ_id.ids),
            "|",
            ("product_tmpl_id", "=", False),
            templates_domain,
            "|",
            ("product_id", "=", False),
            products_domain,
            "|",
            ("date_start", "=", False),
            ("date_start", "<=", date),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", date),
        ]

    def _get_country_pricelist_multi(self, country_ids):
        def get_param_id(key):
            value = self.env["ir.config_parameter"].sudo().get_param(key)
            try:
                return int(value) if value else None
            except TypeError, ValueError:
                return None

        company_id = self.env.company.id
        pl_domain = Domain(self._get_domain_partner_pricelist_multi_search(company_id))

        country_ids = list(country_ids)
        if (ctx_code := self.env.context.get("country_code")) and (
            ctx_country := self.env["res.country"].search(
                [("code", "=", ctx_code)], limit=1
            )
        ):
            if ctx_country.id not in country_ids:
                country_ids.append(ctx_country.id)
        else:
            ctx_country = False

        pl_fallback = (
            self.search(pl_domain & Domain("country_group_ids", "=", False), limit=1)
            or self.browse(
                get_param_id(f"res.partner.property_product_pricelist_{company_id}")
            )
            or self.browse(get_param_id("res.partner.property_product_pricelist"))
            or self.search(pl_domain, limit=1)
        )

        requested = set(country_ids)
        result = {}
        matching_pricelists = self.search(
            pl_domain & Domain("country_group_ids.country_ids", "in", country_ids)
        )
        for pricelist in matching_pricelists:
            covered = requested.intersection(
                pricelist.country_group_ids.country_ids.ids
            )
            for country_id in covered:
                result.setdefault(country_id, pricelist)
        for country_id in country_ids:
            result.setdefault(country_id, pl_fallback)
        result[False] = result[ctx_country.id] if ctx_country else pl_fallback
        return result

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Pricelists"),
                "template": "/product/static/xls/product_pricelist.xls",
            }
        ]

    @api.model
    def _get_partner_pricelist_multi(self, partner_ids):
        ProductPricelist = self.env["product.pricelist"]

        if not self.env["res.groups"]._is_feature_enabled(
            "product.group_product_pricelist"
        ):
            return defaultdict(lambda: ProductPricelist)

        Partner = self.env["res.partner"].with_context(active_test=False)

        result = defaultdict(lambda: ProductPricelist)
        remaining_partner_ids = []
        for partner in Partner.browse(partner_ids):
            if partner.specific_property_product_pricelist._filtered_partner_pricelist_multi():
                result[partner.id] = partner.specific_property_product_pricelist
            else:
                remaining_partner_ids.append(partner.id)

        if remaining_partner_ids:
            remaining_partners = self.env["res.partner"].browse(remaining_partner_ids)
            partners_by_country = remaining_partners.grouped("country_id")
            country_ids = remaining_partners.country_id.ids
            pricelists_by_country_id = self._get_country_pricelist_multi(country_ids)

            for country, partners in partners_by_country.items():
                pl = pricelists_by_country_id[country.id]
                result.update(dict.fromkeys(partners._ids, pl))

        return result

    def _get_domain_partner_pricelist_multi_search(self, company_id):
        return [
            ("active", "=", True),
            ("company_id", "in", [company_id, False]),
        ]

    def _filtered_partner_pricelist_multi(self):
        return self.filtered("active")

    def _get_products_price(self, products, *args, **kwargs):
        self and self.check_singleton()
        return {
            product_id: res_tuple[0]
            for product_id, res_tuple in self._get_price_rule(
                products, *args, **kwargs
            ).items()
        }

    def _get_product_price(self, product, *args, **kwargs):
        self and self.check_singleton()
        return self._get_price_rule(product, *args, **kwargs)[product.id][0]

    def _get_product_price_rule(self, product, *args, **kwargs):
        self and self.check_singleton()
        return self._get_price_rule(product, *args, **kwargs)[product.id]

    def _get_product_rule(self, product, *args, **kwargs):
        self and self.check_singleton()
        return self._get_price_rule(product, *args, compute_price=False, **kwargs)[
            product.id
        ][1]

    def _price_get(self, product, quantity, **kwargs):
        return {
            pricelist_id: price_rule[0]
            for pricelist_id, price_rule in self._get_price_rule_multi(
                product, quantity, **kwargs
            )[product.id].items()
        }
