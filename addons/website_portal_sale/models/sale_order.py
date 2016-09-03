# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.multi
    def get_access_action(self):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the online quote if exists. """
        self.ensure_one()
        if self.state in ['draft', 'cancel']:
            return super(SaleOrder, self).get_access_action()
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/orders/%s' % self.id,
            'target': 'self',
            'res_id': self.id,
        }

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

