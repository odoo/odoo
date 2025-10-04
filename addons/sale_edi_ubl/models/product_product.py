# Part of Odoo. See LICENSE file for full copyright and licensing details.

import bisect

from odoo import fields, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = 'product.product'

    customer_product_ref_ids = fields.One2many(
        comodel_name='customer.product.reference',
        inverse_name='product_id',
        string="Partner References",
    )

    def _order_edi_set_customer_product_ref(self, partner, product_ref):
        """Set customer product reference on product to be able to use that reference for next
        Order extraction to set proper product from that reference.

        Note: self.ensure_one()

        :param recordset partner: Customer for which we are storing product reference.
        :param str product_ref: Product reference in customer database.
        :return: None
        """
        self.ensure_one()

        matching_partner_ref = self.env['customer.product.reference'].search([
            ('partner_id', '=', partner.id),
            ('customer_product_reference', '=', product_ref),
        ], limit=1)
        if matching_partner_ref:
            if matching_partner_ref.product_id != self:
                # update to latest product
                matching_partner_ref.product_id = self
        else:
            self.env['customer.product.reference'].create({
                'partner_id': partner.id,
                'product_id': self.id,
                'customer_product_reference': product_ref,
            })

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
