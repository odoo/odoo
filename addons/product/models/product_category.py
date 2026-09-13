from odoo import _, _lt, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ProductCategory(models.Model):
    _name = "product.category"
    _inherit = ["mixin.mail.thread", "mixin.hierarchy"]
    _description = "Product Category"
    _parent_name = "parent_id"
    _rec_name = "complete_name"
    _order = "complete_name"
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(
        index="trigram",
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the category without removing it.",
    )
    parent_id = fields.Many2one(
        comodel_name="product.category",
        string="Parent Category",
        index=True,
        ondelete="restrict",
    )
    complete_name = fields.Char(
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )
    child_id = fields.One2many(
        comodel_name="product.category",
        inverse_name="parent_id",
        string="Child Categories",
    )
    product_tmpl_ids = fields.One2many(
        comodel_name="product.template",
        inverse_name="categ_id",
        string="Products",
    )
    product_count = fields.Integer(
        string="# Products",
        compute="_compute_product_count",
        recursive=True,
        help="The number of products under this category and its children.",
    )
    product_properties_definition = fields.PropertiesDefinition(
        string="Product Properties"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        tracking=True,
        help="Keep empty to share this category with every company.",
    )

    _hierarchy_cycle_message = _lt("You cannot create recursive categories.")

    @api.constrains("company_id")
    def _check_company_id(self):
        for company, categories in self.grouped("company_id").items():
            if not company:
                # A shared category stays usable by every company's products.
                continue
            # A product may use a category of its own company or of an ancestor
            # (see _check_company_domain above), so the products to reject are the
            # ones whose company is not below this one -- shared products included.
            domain = Domain("categ_id", "in", categories.ids) & ~Domain(
                "company_id", "child_of", company.id
            )
            if not self.env["product.template"].sudo().search_count(domain, limit=1):  # noqa: E8507 - one probe per company; categories sharing one were merged above
                continue
            raise ValidationError(
                self.env._(
                    "You cannot restrict %(categories)s to %(company)s: it holds"
                    " products shared between companies or belonging to another"
                    " company.",
                    categories=", ".join(categories.mapped("display_name")),
                    company=company.display_name,
                )
            )

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for category, vals in zip(self, vals_list, strict=True):
                if vals is None:
                    continue
                vals["name"] = _("%s (copy)", category.name)
        return vals_list

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = "%s / %s" % (
                    category.parent_id.complete_name,
                    category.name,
                )
            else:
                category.complete_name = category.name

    @api.depends("product_tmpl_ids", "child_id.product_count")
    def _compute_product_count(self):
        read_group_res = self.env["product.template"]._read_group(
            [("categ_id", "child_of", self.ids)], ["categ_id"], ["__count"]
        )
        self_ids = set(self.ids)
        count_by_categ = {}
        for categ, count in read_group_res:
            for ancestor_id in categ._get_ancestor_ids(include_self=True):
                if ancestor_id in self_ids:
                    count_by_categ[ancestor_id] = (
                        count_by_categ.get(ancestor_id, 0) + count
                    )
        for categ in self:
            categ.product_count = count_by_categ.get(categ.id, 0)

    @api.depends_context("hierarchical_naming")
    def _compute_display_name(self):
        if self.env.context.get("hierarchical_naming", True):
            return super()._compute_display_name()
        for record in self:
            record.display_name = record.name
        return None

    @api.model
    def name_create(self, name):
        category = self.create({"name": name})
        return category.id, category.display_name
