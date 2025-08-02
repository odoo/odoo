# Copyright 2021 VentorTech OU
# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    barcode_ids = fields.One2many(
        'product.barcode.multi',
        'product_id',
        string='Additional Barcodes',
    )
    tenant_id = fields.Char(related='product_tmpl_id.tenant_id', store=True)

    # THIS IS OVERRIDE SQL CONSTRAINTS.
    _sql_constraints = [
        ('barcode_uniq', 'check(1=1)', 'No error')
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, order=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('default_code', operator, name),
                      '|', ('barcode', operator, name), ('barcode_ids', operator, name)]
        return self._search(expression.AND([domain, args]),
                                  limit=limit, order=order)

    @api.constrains('barcode', 'barcode_ids', 'active')
    def _check_unique_barcode(self):
        for product in self:
            tenant = product.tenant_id
            if not tenant:
                continue  # skip check if tenant not set

            all_barcodes = set()
            if product.barcode:
                all_barcodes.add(product.barcode)
            all_barcodes.update(product.barcode_ids.mapped('name'))

            if not all_barcodes:
                continue

            # Check other products with same tenant and same barcode
            domain = [
                ('id', '!=', product.id),
                ('active', '=', True),
                ('tenant_id', '=', tenant),
                '|',
                ('barcode', 'in', list(all_barcodes)),
                ('barcode_ids.name', 'in', list(all_barcodes))
            ]
            conflict_products = self.env['product.product'].search(domain)

            conflict_barcodes = set()
            for cp in conflict_products:
                if cp.barcode in all_barcodes:
                    conflict_barcodes.add(cp.barcode)
                conflict_barcodes.update(
                    cp.barcode_ids.filtered(lambda b: b.name in all_barcodes).mapped('name')
                )

            if conflict_barcodes:
                raise UserError(_(
                    "The following barcode(s): %s are already used in another product within the same tenant (%s)."
                ) % (", ".join(conflict_barcodes), tenant))

