# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _compute_purchase_order_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        purchase_order_groups = self.env['purchase.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            fields=['partner_id'], groupby=['partner_id']
        )
        partners = self.browse()
        for group in purchase_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.purchase_order_count += group['partner_id_count']
                    partners |= partner
                partner = partner.parent_id
        (self - partners).purchase_order_count = 0

    def _compute_supplier_invoice_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        supplier_invoice_groups = self.env['account.move']._read_group(
            domain=[('partner_id', 'in', all_partners.ids),
                    ('move_type', 'in', ('in_invoice', 'in_refund'))],
            fields=['partner_id'], groupby=['partner_id']
        )
        partners = self.browse()
        for group in supplier_invoice_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.supplier_invoice_count += group['partner_id_count']
                    partners |= partner
                partner = partner.parent_id
        (self - partners).supplier_invoice_count = 0

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

    receipt_reminder_email = fields.Boolean('Receipt Reminder', default=False, company_dependent=True,
        help="Automatically send a confirmation email to the vendor X days before the expected receipt date, asking him to confirm the exact date.")
    reminder_date_before_receipt = fields.Integer('Days Before Receipt', default=1, company_dependent=True,
        help="Number of days to send reminder email before the promised receipt date")
