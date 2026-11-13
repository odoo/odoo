# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    days_to_purchase = fields.Integer(
        string='Days to Purchase',
        help="Days needed to confirm a PO, define when a PO should be validated")
    freight_product_id = fields.Many2one(
        'product.product', string="Freight Product",
        domain=[('type', '=', 'service'), ('purchase_ok', '=', True)],
        check_company=True,
        help="Product of the requests for quotation sent to carriers for the transport of deliveries.")

    def _get_freight_product(self):
        """ The product of the freight requests for quotation, created the first time it is needed. """
        self.ensure_one()
        if not self.freight_product_id:
            if not (
                self.env['product.product'].has_access('create')
                and self.has_access('write')
                and self.has_field_access(self._fields['freight_product_id'], 'write')
            ):
                raise UserError(_(
                    "There is no freight product configured for this company yet. Ask an administrator to set one "
                    "in the Purchase settings, or to request a freight quotation the first time."))
            self.freight_product_id = self.env['product.product'].create({
                'name': _("Freight"),
                'type': 'service',
                'purchase_ok': True,
                'sale_ok': False,
            })
        return self.freight_product_id
