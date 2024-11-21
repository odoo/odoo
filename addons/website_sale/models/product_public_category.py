# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
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
    sequence = fields.Integer(default=_default_sequence, index=True)

    parent_id = fields.Many2one(
        string="Parent Category",
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

    website_description = fields.Html(
        string="Category Description",
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

    #=== COMPUTE METHODS ===#

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

    #=== CONSTRAINT METHODS ===#

    @api.constrains('parent_id')
    def check_parent_id(self):
        if self._has_cycle():
            raise ValueError(self.env._("Error! You cannot create recursive categories."))

    #=== BUSINESS METHODS ===#

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
