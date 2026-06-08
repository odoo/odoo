# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CustomerProductReference(models.Model):
    _name = 'customer.product.reference'
    _description = "Customer Product Reference"

    product_id = fields.Many2one(
        comodel_name='product.product',
        index=True,
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        required=True,
        ondelete='cascade',
    )
    customer_product_reference = fields.Char(required=True)

    _product_partner_unique = models.Constraint(
        'unique (product_id, partner_id)',
        'The customer reference with the same product and partner already exists!',
    )

    @api.model
    def create_or_update_product_reference(self, partner, product, reference):
        """Set customer product reference on product to be able to use that reference for next
        Order extraction to set proper product from that reference.

        Note: self.ensure_one()

        :param recordset product: Product for which we are storing customer product reference.
        :param recordset partner: Customer for which we are storing product reference.
        :param str reference: Product reference in customer database.
        :return: None
        """

        matching_partner_ref = self._find_matching_ref(partner, reference)
        if not matching_partner_ref:
            self.create({
                'partner_id': partner.id,
                'product_id': product.id,
                'customer_product_reference': reference,
            })
        elif matching_partner_ref.product_id != product:
            # Update to the latest product.
            matching_partner_ref.product_id = product

    @api.model
    def find_product_matching_reference(self, partner, reference):
        """Find the product linked to the given customer and product reference.

        :param res.partner partner: The customer to look up.
        :param str reference: The product reference to look up.
        :return: The corresponding product.
        :rtype: product.product
        """
        return self._find_matching_ref(partner, reference).product_id

    @api.model
    def _find_matching_ref(self, partner, product_ref):
        """Find the customer product reference linked to the given customer and product reference.

        :param res.partner partner: The customer to look up.
        :param str product_ref: The product reference to look up.
        :return: The corresponding customer product reference.
        :rtype: customer.product.reference
        """
        return self.search([
            ('partner_id', '=', partner.id),
            ('customer_product_reference', '=', product_ref),
        ], limit=1)
