# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    @api.multi
    def _purchase_invoice_count(self):
        PurchaseOrder = self.env['purchase.order']
        Invoice = self.env['account.invoice']
        for partner in self:
            partner.purchase_order_count = PurchaseOrder.search_count([('partner_id', 'child_of', partner.id)])
            partner.supplier_invoice_count = Invoice.search_count([('partner_id', 'child_of', partner.id), ('type', '=', 'in_invoice')])

    @api.model
    def _commercial_fields(self):
        return super(res_partner, self)._commercial_fields()

    property_purchase_currency_id = fields.Many2one(
        'res.currency', string="Supplier Currency", company_dependent=True,
        help="This currency will be used, instead of the default one, for purchases from the current partner")
    purchase_order_count = fields.Integer(compute='_purchase_invoice_count', string='# of Purchase Order')
    supplier_invoice_count = fields.Integer(compute='_purchase_invoice_count', string='# Vendor Bills')
