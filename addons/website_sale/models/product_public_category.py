# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.translate import html_translate


class ProductPublicCategory(models.Model):
    _name = 'product.public.category'
    _inherit = [
        'website.seo.metadata',
        'website.multi.mixin',
        'website.searchable.mixin',
        'image.mixin',
    ]
    _description = "Website Product Category"
    _parent_store = True
    _order = 'sequence, name, id'

    def _default_sequence(self):
        cat = self.search([], limit=1, order='sequence DESC')
        if cat:
            return cat.sequence + 5
        return 10000

    name = fields.Char(required=True, translate=True)
    cover_image = fields.Image(
        string="Cover Image", help="Displayed only in the Category List Snippet.",
    )
    sequence = fields.Integer(default=_default_sequence, index=True)

    parent_id = fields.Many2one(
        string="Parent",
        comodel_name='product.public.category',
        ondelete='cascade',
        index=True,
    )
    child_id = fields.One2many(
        string="Children Categories",
        comodel_name='product.public.category',
        inverse_name='parent_id',
    )
    parent_path = fields.Char(index=True)
    parents_and_self = fields.Many2many(
        comodel_name='product.public.category',
        compute='_compute_parents_and_self',
    )

    product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_public_category_product_template_rel',
    )
    has_published_products = fields.Boolean(
        compute='_compute_has_published_products',
        search='_search_has_published_products',
        compute_sudo=True,
        recursive=True,
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

    show_category_title = fields.Boolean(
        string="Show Category Title",
        default=False,
        help="Display the category title on the shop page. Corresponds to the 'Show Title' editor option."
    )

    show_category_description = fields.Boolean(
        string="Show Category Description",
        default=True,
        help="Display the category description on the shop page. Corresponds to the 'Show Description' editor option."
    )

    align_category_content = fields.Boolean(
        string="Align Category Content",
        default=False,
        help="Align the category content on the shop page. Corresponds to the 'Center Content' editor option."
    )

    # === COMPUTE METHODS === #

    @api.depends('parent_path')
    def _compute_parents_and_self(self):
        for category in self:
            if category.parent_path:
                category.parents_and_self = self.env['product.public.category'].browse([int(p) for p in category.parent_path.split('/')[:-1]])
            else:
                category.parents_and_self = category

    @api.depends('parents_and_self')
    def _compute_display_name(self):
        for category in self:
            category.display_name = " / ".join(category.parents_and_self.mapped(
                lambda cat: cat.name or self.env._("New")
            ))

    @api.depends('product_tmpl_ids.is_published', 'child_id.has_published_products')
    def _compute_has_published_products(self):
        grouped_product_templates = self.env['product.template']._read_group(
            domain=[('public_categ_ids', 'in', self.ids), ('is_published', '=', True), ('active', '=', True)],
            groupby=['public_categ_ids']
        )
        published_category_ids = {group[0].id for group in grouped_product_templates}
        for category in self:
            has_published = category.id in published_category_ids
            category.has_published_products = (
                has_published or any(c.has_published_products for c in category.child_id)
            )

    # === CONSTRAINT METHODS === #

    @api.constrains('parent_id')
    def check_parent_id(self):
        if self._has_cycle():
            raise ValueError(self.env._("Error! You cannot create recursive categories."))

    # === SEARCH METHODS === #

    @api.model
    def _search_has_published_products(self, operator, value):
        if operator != 'in':
            return NotImplemented
        published_categ_ids = self._search(
            [('product_tmpl_ids', 'any', [('is_published', '=', True), ('active', '=', True)])]
        ).get_result_ids()
        # Note that if the `value` is False, the ORM will invert the domain below
        return [
            '|',
            ('id', 'in', published_categ_ids),
            ('id', 'parent_of', published_categ_ids),
        ]

    # === BUSINESS METHODS === #

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        search_fields = ['name']
        fetch_fields = ['id', 'name']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('website_description')
            fetch_fields.append('website_description')
            mapping['description'] = {'name': 'website_description', 'type': 'text', 'match': True, 'html': True}
        return {
            'model': 'product.public.category',
            'base_domain': [website.website_domain()],
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-folder-o',
            'order': 'name desc, id desc' if 'name desc' in order else 'name asc, id desc',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for data in results_data:
            data['url'] = '/shop/category/%s' % data['id']
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
            aggregates=['id:count'],
            groupby=['parent_id'],
        )
        return [{
            'id': parent_category.id,
            'name': f'{parent_category.name} ({child_count})',
        } for parent_category, child_count in child_count_by_parent if parent_category]

    @api.model
    def _get_available_category_domain(self, website_id):
        """Build a search domain for product categories to be used in dynamic snippets.

        :param int website_id: ID of the current website
        :return: A domain to filter product categories for the given website
        :rtype: Domain
        """
        domain = Domain('website_id', 'in', [False, website_id])
        # Public and portal users should only see categories with published products.
        if not self.env.user.has_group('website.group_website_designer'):
            domain &= Domain('has_published_products', '=', True)
        return domain
