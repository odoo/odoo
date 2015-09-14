# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    requisition_id = fields.Many2one('purchase.requisition', string='Call for Tenders', copy=False)

    @api.multi
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        ProcurementOrder = self.env['procurement.order']
        for po in self:
            if po.requisition_id.exclusive == 'exclusive':
                for order in po.requisition_id.purchase_ids:
                    if order.id != po.id:
                        procurement = ProcurementOrder.search([('purchase_id', '=', order.id)])
                        if procurement and po.state == 'confirmed':
                            procurement.write({'purchase_id': po.id})
                        order.button_cancel()
                    po.requisition_id.tender_done()
            for element in po.order_line:
                if not element.quantity_tendered:
                    element.write({'quantity_tendered': element.product_qty})
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    quantity_tendered = fields.Float(string='Quantity Tendered', digits_compute=dp.get_precision('Product Unit of Measure'), help="Technical field for not loosing the initial information about the quantity proposed in the tender", oldname='quantity_bid')

    @api.model
    def generate_po(self, tender_id):
        #call generate_po from tender with active_id. Called from js widget
        return self.env['purchase.requisition'].browse(tender_id).generate_po()

    @api.multi
    def button_confirm(self):
        for element in self:
            element.write({'quantity_tendered': element.product_qty})

    @api.multi
    def button_cancel(self):
        self.write({'quantity_tendered': 0})
