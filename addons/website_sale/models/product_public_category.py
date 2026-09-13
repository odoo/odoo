from odoo import _lt, api, fields, models
from odoo.fields import Domain
from odoo.tools.translate import html_translate


class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = [
        "mixin.website.seo.metadata",
        "mixin.website.multi",
        "mixin.website.searchable",
        "mixin.image",
        "mixin.hierarchy",
    ]
    _description = "Website Product Category"
    _order = "sequence, name, id"

    def _default_sequence(self):
        cat = self.search([], limit=1, order="sequence DESC")
        if cat:
            return cat.sequence + 5
        return 10000

    name = fields.Char(
        translate=True,
        required=True,
    )
    cover_image = fields.Image(help="Displayed only in the Category List Snippet.")
    sequence = fields.Integer(
        default=_default_sequence,
        index=True,
    )

    parent_id = fields.Many2one(
        comodel_name="product.public.category",
        index=True,
        ondelete="cascade",
    )
    child_id = fields.One2many(
        comodel_name="product.public.category",
        inverse_name="parent_id",
        string="Children Categories",
    )
    parents_and_self = fields.Many2many(
        comodel_name="product.public.category",
        compute="_compute_parents_and_self",
    )

    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        relation="product_public_category_product_template_rel",
    )
    has_published_products = fields.Boolean(
        compute="_compute_has_published_products",
        search="_search_has_published_products",
        compute_sudo=True,
        recursive=True,
    )

    website_description = fields.Html(
        string="Description",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
    )

    website_footer = fields.Html(
        string="Category Footer",
        translate=html_translate,
        sanitize_attributes=False,
        sanitize_form=False,
    )

    show_category_title = fields.Boolean(
        default=False,
        help="Display the category title on the shop page. Corresponds to the 'Show Title' editor option.",
    )

    show_category_description = fields.Boolean(
        default=True,
        help="Display the category description on the shop page. Corresponds to the 'Show Description' editor option.",
    )

    align_category_content = fields.Boolean(
        default=False,
        help="Align the category content on the shop page. Corresponds to the 'Center Content' editor option.",
    )

    @api.depends("parent_path")
    def _compute_parents_and_self(self):
        for category in self:
            category.parents_and_self = (
                self.browse(category._get_ancestor_ids(include_self=True)) or category
            )

    @api.depends("parents_and_self")
    def _compute_display_name(self):
        for category in self:
            category.display_name = " / ".join(
                category.parents_and_self.mapped(
                    lambda cat: cat.name or self.env._("New")
                )
            )

    @api.depends("product_tmpl_ids.is_published", "child_id.has_published_products")
    def _compute_has_published_products(self):
        grouped_product_templates = self.env["product.template"]._read_group(
            domain=[
                ("public_categ_ids", "in", self.ids),
                ("is_published", "=", True),
                ("active", "=", True),
            ],
            groupby=["public_categ_ids"],
        )
        published_category_ids = {group[0].id for group in grouped_product_templates}
        for category in self:
            has_published = category.id in published_category_ids
            category.has_published_products = has_published or any(
                c.has_published_products for c in category.child_id
            )

    _hierarchy_cycle_message = _lt("Error! You cannot create recursive categories.")

    @api.model
    def _search_has_published_products(self, operator, value):
        if operator != "in":
            return NotImplemented
        published_categ_ids = self._search(
            [
                (
                    "product_tmpl_ids",
                    "any",
                    [("is_published", "=", True), ("active", "=", True)],
                )
            ]
        ).get_result_ids()
        return [
            "|",
            ("id", "in", published_categ_ids),
            ("id", "parent_of", published_categ_ids),
        ]

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options["displayDescription"]
        search_fields = ["name"]
        fetch_fields = ["id", "name"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "url", "type": "text", "truncate": False},
        }
        if with_description:
            search_fields.append("website_description")
            fetch_fields.append("website_description")
            mapping["description"] = {
                "name": "website_description",
                "type": "text",
                "match": True,
                "html": True,
            }
        return {
            "model": "product.public.category",
            "base_domain": [website.website_domain()],
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-regular fa-folder",
            "order": "name desc, id desc"
            if "name desc" in order
            else "name asc, id desc",
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(
            fetch_fields, mapping, icon, limit
        )
        for data in results_data:
            data["url"] = "/shop/category/%s" % data["id"]
        return results_data

    @api.model
    def get_available_snippet_categories(self, website_id):
        child_count_by_parent = self._read_group(
            domain=self._get_domain_available_category(website_id),
            aggregates=["id:count"],
            groupby=["parent_id"],
        )
        return [
            {
                "id": parent_category.id,
                "name": f"{parent_category.name} ({child_count})",
            }
            for parent_category, child_count in child_count_by_parent
            if parent_category
        ]

    @api.model
    def _get_domain_available_category(self, website_id):
        domain = Domain("website_id", "in", [False, website_id])
        if not self.env.user.has_group("website.group_website_designer"):
            domain &= Domain("has_published_products", "=", True)
        return domain
