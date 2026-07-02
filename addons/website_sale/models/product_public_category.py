# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.sql import SQL
from odoo.tools.translate import html_translate

from odoo.addons.website_sale.const import SHOP_PATH


class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = [
        "website.seo.metadata",
        "website.published.multi.mixin",
        "website.located.mixin",
        "website.searchable.mixin",
        "image.mixin",
    ]
    _description = "Website Product Category"
    _parent_store = True
    _order = "sequence, name, id"

    def _default_sequence(self):
        cat = self.search([], limit=1, order="sequence DESC")
        if cat:
            return cat.sequence + 5
        return 10000

    name = fields.Char(required=True, translate=True)
    cover_image = fields.Image(
        string="Cover Image", help="Displayed only in the Category List Snippet."
    )
    is_published = fields.Boolean(compute="_compute_is_published")
    not_in_shop = fields.Boolean(
        string="Not in Shop",
        help="If checked, the category will not be displayed in the main catalog page",
        compute="_compute_not_in_shop",
        store=True,
        readonly=False,
        recursive=True,
    )
    sequence = fields.Integer(default=_default_sequence, index=True)

    parent_id = fields.Many2one(
        string="Parent", comodel_name="product.public.category", ondelete="cascade", index=True
    )
    child_id = fields.One2many(
        string="Children Categories",
        comodel_name="product.public.category",
        inverse_name="parent_id",
    )
    parent_path = fields.Char(index=True)
    parents_and_self = fields.Many2many(
        comodel_name="product.public.category", compute="_compute_parents_and_self"
    )

    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template", relation="product_public_category_product_template_rel"
    )
    has_published_products = fields.Boolean(
        compute="_compute_has_published_products",
        search="_search_has_published_products",
        compute_sudo=True,
    )

    website_description = fields.Html(
        string="Description",
        sanitize_attributes=False,
        sanitize_form=False,
        sanitize_overridable=True,
        translate=html_translate,
    )

    website_footer = fields.Html(
        string="Category Footer",
        sanitize_attributes=False,
        sanitize_form=False,
        translate=html_translate,
    )

    # === COMPUTE METHODS === #

    @api.depends("has_published_products")
    def _compute_is_published(self):
        for category in self:
            category.is_published = category.has_published_products

    @api.depends("parent_id.not_in_shop")
    def _compute_not_in_shop(self):
        for category in self:
            if category.parent_id:
                category.not_in_shop = category.parent_id.not_in_shop

    @api.depends("parent_path")
    def _compute_parents_and_self(self):
        for category in self:
            if category.parent_path:
                category.parents_and_self = self.env["product.public.category"].browse([
                    int(p) for p in category.parent_path.split("/")[:-1]
                ])
            else:
                category.parents_and_self = category

    @api.depends("parents_and_self")
    @api.depends_context("show_parent_categories")
    def _compute_display_name(self):
        """Override to include the parent category names in the category's display name.

        By default, parent category names are included, but they can be excluded by setting the
        `show_parent_categories` context key to `False`.
        """
        if not self.env.context.get("show_parent_categories", True):
            super()._compute_display_name()
            return
        for category in self:
            category.display_name = " / ".join(
                category.parents_and_self.mapped(lambda cat: cat.name or self.env._("New"))
            )

    def _compute_website_url(self):
        super()._compute_website_url()
        slug = self.env["ir.http"]._slug
        for category in self:
            if category.id:
                # Only take the current category and its 4 closest parents to avoid having too long
                # URLs. This number should stay in sync with the category route computation.
                category_slugs = [slug(cat) for cat in category.parents_and_self[-5:]]
                category.website_url = f"{SHOP_PATH}/category/%s" % "/".join(category_slugs)

    @api.depends_context("company", "website_id")
    def _compute_has_published_products(self):
        has_published_products = self.search(
            # See also :meth:`_search_has_published_products`
            Domain([("has_published_products", "=", True), ("id", "in", self.ids)]),
            order="id",
        )
        has_published_products.has_published_products = True
        (self - has_published_products).has_published_products = False

    # === SEARCH METHODS === #

    @api.model
    def _search_has_published_products(self, operator, value):
        if not (operator == "in" and True in value):
            return NotImplemented

        published_products_domain = (
            Domain([("active", "=", True), ("is_published", "=", True)])
            & self.env["website"].sale_product_domain()
        )
        # Bypass access rules in the subquery to avoid adding `has_published_products = True` twice.
        subquery = self._search(
            Domain("product_tmpl_ids", "any", published_products_domain), bypass_access=True
        )
        parents_and_self_have_published_products = SQL(
            "SELECT unnest(string_to_array(left(c.parent_path, -1), '/'))::integer FROM %s c",
            subquery.subselect(subquery.table.parent_path),
        )

        return Domain("id", "any", parents_and_self_have_published_products)

    # === BUSINESS METHODS === #

    @api.model
    def _search_get_detail(self, website, order, options):  # noqa: ARG002
        search_fields = ["name", "website_description"]
        fetch_fields = ["id", "name", "parents_and_self", "website_description"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "url", "type": "text", "truncate": False},
            "search_item_metadata": {
                "name": "breadcrumb",
                "type": "text",
                "truncate": False,
                "match": True,
            },
            "image_url": {"name": "image_url", "type": "html"},
            "description": {
                "name": "website_description",
                "type": "text",
                "html": True,
                "match": True,
            },
        }
        return {
            "model": "product.public.category",
            "base_domain": [website.website_domain()],
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-folder-o",
            "order": "name desc, id desc" if "name desc" in order else "name asc, id desc",
            "group_name": self.env._("Categories"),
            "sequence": 30,
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        product_category_model = self.env["product.public.category"]
        for data in results_data:
            data["url"] = "/shop/category/%s" % data["id"]
            data["image_url"] = "/web/image/product.public.category/%s/image_128" % data["id"]
            category_ids = data.get("parents_and_self", [])
            category_names = product_category_model.browse(category_ids[:-1]).mapped("name")
            data["breadcrumb"] = " / ".join(category_names)
        return results_data

    @api.model
    def get_available_snippet_categories(self, website_id):
        """Return parent categories available for selection in the dynamic category snippet.

        :param int website_id: ID of the current website
        :return: Available parent categories
        :rtype: list[dict]
        """
        child_count_by_parent = self._read_group(
            domain=self._get_available_category_domain(website_id),
            aggregates=["id:count"],
            groupby=["parent_id"],
        )
        return [
            {"id": parent_category.id, "name": f"{parent_category.name} ({child_count})"}
            for parent_category, child_count in child_count_by_parent
            if parent_category
        ]

    @api.model
    def _get_available_category_domain(self, website_id):
        """Build a search domain for product categories to be used in dynamic snippets.

        :param int website_id: ID of the current website
        :return: A domain to filter product categories for the given website
        :rtype: Domain
        """
        domain = Domain("website_id", "in", [False, website_id])
        # Public and portal users should only see categories with published products.
        if not self.env.user.has_group("website.group_website_designer"):
            domain &= Domain("has_published_products", "=", True)
        return domain
