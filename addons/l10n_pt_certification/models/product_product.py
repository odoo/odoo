from odoo import api, models
from odoo.fields import Domain

from odoo.addons.l10n_pt_certification.models.product_template import (
    _l10n_pt_format_display_name,
    _l10n_pt_read_pt_names,
    _l10n_pt_search_pt_name,
)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, values):
        res = super().create(values)
        for product in res:
            # Products should have a unique default code for Portugal.
            if 'PT' in product.fiscal_country_codes and not product.default_code:
                product.default_code = f"{product.name.replace(' ', '_').upper()[:4]}_{product.id}"
        return res

    @api.depends('product_tmpl_id.l10n_pt_product_name')
    @api.depends_context('company', 'l10n_pt_frozen_product_name')
    def _compute_display_name(self):
        # EXTENDS product
        # Portuguese companies and their documents name a product by its name on Portuguese documents.
        super()._compute_display_name()
        if self.env['product.template']._l10n_pt_shows_pt_name():
            # sudo: as core's compute, which checked the access to the products, the variants' attribute
            # values are read whatever the user's access to them.
            for product in self.sudo().filtered(lambda product: product.product_tmpl_id.l10n_pt_product_name):
                pt_name = product.product_tmpl_id.l10n_pt_product_name
                variant = product.product_template_attribute_value_ids._get_combination_name()
                product.display_name = _l10n_pt_format_display_name(
                    self.env, f"{pt_name} ({variant})" if variant else pt_name, product.default_code,
                )

    @api.model
    def _search_display_name(self, operator, value):
        # EXTENDS product
        domain = super()._search_display_name(operator, value)
        if self.env['product.template']._l10n_pt_shows_pt_name():
            return _l10n_pt_search_pt_name(domain, operator, value)
        return domain

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        # EXTENDS product
        # A Portuguese company also finds a product by its name on Portuguese documents; core's search
        # of variants reads `name` itself, not `_search_display_name`.
        result = super().name_search(name, domain, operator, limit)
        if (
            name and operator not in Domain.NEGATIVE_OPERATORS and (not limit or len(result) < limit)
            and self.env['product.template']._l10n_pt_shows_pt_name()
        ):
            found_ids = [product_id for product_id, _display_name in result]
            products = self.search_fetch(
                Domain(domain or Domain.TRUE) & Domain('l10n_pt_product_name', operator, name) & Domain('id', 'not in', found_ids),
                ['display_name'],
                limit=limit and limit - len(result),
            )
            # sudo: as core's, which reads the display names of the products found whatever the user's
            # access to their attribute values.
            result += [(product.id, product.display_name) for product in products.sudo()]
        return result

    def read(self, fields=None, load='_classic_read'):
        # EXTENDS base
        # As the template's: a Portuguese company sees a product by its name on Portuguese documents.
        values_list = super().read(fields, load)
        if (not fields or 'name' in fields) and self.env['product.template']._l10n_pt_shows_pt_name():
            _l10n_pt_read_pt_names(self, values_list)
        return values_list
