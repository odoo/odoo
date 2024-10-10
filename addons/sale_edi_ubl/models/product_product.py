# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    partner_references_ids = fields.One2many(
        comodel_name='product.partner.reference',
        inverse_name='product_id',
        string="Partner References",
    )

    def _edi_set_customer_product_ref(self, partner, product_ref):
        """ Set customer product reference on product to be able to use that reference for next
        Order extraction to set proper product from that reference.

        Note: self.ensure_one()

        :partner: Customer for which we are storing product reference.
        :product_ref: Product reference in customer database.
        """
        self.ensure_one()

        matching_partner_ref = self.partner_references_ids.filtered(
            lambda partner_ref: partner_ref.partner_id == partner and partner_ref.product_id == self
        )
        if matching_partner_ref:
            if matching_partner_ref.partner_product_reference != product_ref:
                # update to latest partner's product reference
                matching_partner_ref.partner_product_reference = product_ref
        else:
            self.env['product.partner.reference'].create({
                'partner_id': partner.id,
                'product_id': self.id,
                'partner_product_reference': product_ref,
            })
