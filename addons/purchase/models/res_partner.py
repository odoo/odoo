# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    @api.multi
    def _compute_purchase_order_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        purchase_order_groups = self.env['purchase.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            fields=['partner_id'], groupby=['partner_id']
        )
        for group in purchase_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.purchase_order_count += group['partner_id_count']
                partner = partner.parent_id

    @api.multi
    def _compute_supplier_invoice_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        supplier_invoice_groups = self.env['account.invoice'].read_group(
            domain=[('partner_id', 'in', all_partners.ids),
                    ('type', 'in', ['in_invoice', 'in_refund'])],
            fields=['partner_id'], groupby=['partner_id']
        )
        for group in supplier_invoice_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.supplier_invoice_count += group['partner_id_count']
                partner = partner.parent_id

    @api.model
    def _commercial_fields(self):
        return super(res_partner, self)._commercial_fields()

    property_purchase_currency_id = fields.Many2one(
        'res.currency', string="Supplier Currency", company_dependent=True,
        help="This currency will be used, instead of the default one, for purchases from the current partner")
    purchase_order_count = fields.Integer(compute='_compute_purchase_order_count', string='Purchase Order Count')
    supplier_invoice_count = fields.Integer(compute='_compute_supplier_invoice_count', string='# Vendor Bills')
    purchase_warn = fields.Selection(WARNING_MESSAGE, 'Purchase Order', help=WARNING_HELP, default="no-message")
    purchase_warn_msg = fields.Text('Message for Purchase Order')
