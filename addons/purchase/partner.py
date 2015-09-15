# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    @api.multi
    def _purchase_invoice_count(self):
        purchase_data = self.env['purchase.order'].read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        invoice_data = self.env['account.invoice'].read_group([('partner_id', 'in', self.ids), ('type', '=', 'in_invoice')], ['partner_id'], ['partner_id'])
        purchase_mapped_data = dict([(m['partner_id'][0], m['partner_id_count']) for m in purchase_data])
        invoice_mapped_data = dict([(m['partner_id'][0], m['partner_id_count']) for m in invoice_data])
        for partner in self:
            partner.purchase_order_count = purchase_mapped_data.get(partner.id, 0)
            partner.supplier_invoice_count = invoice_mapped_data.get(partner.id, 0)

    @api.model
    def _commercial_fields(self):
        return super(res_partner, self)._commercial_fields()

    property_purchase_currency_id = fields.Many2one('res.currency', string="Supplier Currency",\
      help="This currency will be used, instead of the default one, for purchases from the current partner")
    purchase_order_count = fields.Integer(compute='_purchase_invoice_count', string='# of Purchase Order')
    supplier_invoice_count = fields.Integer(compute='_purchase_invoice_count', string='# Vendor Bills')
