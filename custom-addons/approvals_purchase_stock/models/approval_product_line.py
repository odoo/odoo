# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    def _default_warehouse_id(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', company_id)], limit=1
        )
        return warehouse

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse",
        default=lambda self: self._default_warehouse_id(), check_company=True)

    def _get_picking_type(self):
        """ Returns the picking type for incoming picking, depending of the
        product line warehouse. """
        self.ensure_one()
        if not self.warehouse_id:
            return None
        return self.warehouse_id.in_type_id

    def _get_purchase_orders_domain(self, vendor):
        """ Override to filter purchase orders on warehouse. """
        domain = super()._get_purchase_orders_domain(vendor)
        picking_type = self._get_picking_type()
        if picking_type:
            domain = expression.AND([
                domain,
                [('picking_type_id', '=', picking_type.id)]
            ])
        return domain

    def _get_purchase_order_values(self, vendor):
        vals = super()._get_purchase_order_values(vendor)
        picking_type = self._get_picking_type()
        if picking_type:
            vals['picking_type_id'] = picking_type.id
        return vals
