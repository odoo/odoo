# Part of Odoo. See LICENSE file for full copyright and licensing details.

import bisect

from odoo import models
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
