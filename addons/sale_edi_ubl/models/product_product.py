# Part of Odoo. See LICENSE file for full copyright and licensing details.

import bisect

from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_product_domain_search_order(self, **vals):
        """Override of `account` to include the variant identifiers in the search order.

        If the product is not found using `*ItemIdentification:ID` elements, tries again with the
        `*ItemIdentification:ExtendedID` elements. `ExtendedID` could be used to identify a product
        variant.

        Example:
            StandardItemIdentification::ID == product.template.barcode           (product ID)
            StandardItemIdentification::ExtendedID == product.product.barcode    (variant ID)
        """
        domains = super()._get_product_domain_search_order(**vals)

        if variant_default_code := vals.get('variant_default_code'):
            bisect.insort(domains, (12, Domain('default_code', '=', variant_default_code)))
        if variant_barcode := vals.get('variant_barcode'):
            bisect.insort(domains, (14, Domain('barcode', '=', variant_barcode)))

        return domains

    @api.model
    def _import_retrieve_product_from_variant_default_code(self, product_values):
        if variant_default_code := product_values.get('variant_default_code'):
            return {'criteria': [{'domain': [('default_code', '=', variant_default_code)]}]}

    @api.model
    def _import_retrieve_product_from_variant_barcode(self, product_values):
        if variant_barcode := product_values.get('variant_barcode'):
            return {'criteria': [{'domain': [('barcode', '=', variant_barcode)]}]}

    def _get_retrieval_product_search_plan(self):
        search_plan = super()._get_retrieval_product_search_plan()
        return [
            *search_plan,
            (12, self._import_retrieve_product_from_variant_default_code),
            (14, self._import_retrieve_product_from_variant_barcode),
        ]
