# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.osv import expression

class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Sale Order Count')
    sale_order_ids = fields.One2many('sale.order', 'partner_id', 'Sales Order')
    sale_warn = fields.Selection(WARNING_MESSAGE, 'Sales Warnings', default='no-message', help=WARNING_HELP)
    sale_warn_msg = fields.Text('Message for Sales Order')

    @api.model
    def _get_sale_order_domain_count(self):
        return []

    def _compute_sale_order_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        sale_order_groups = self.env['sale.order']._read_group(
            domain=expression.AND([self._get_sale_order_domain_count(), [('partner_id', 'in', all_partners.ids)]]),
            fields=['partner_id'], groupby=['partner_id']
        )
        partners = self.browse()
        for group in sale_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.sale_order_count += group['partner_id_count']
                    partners |= partner
                partner = partner.parent_id
        (self - partners).sale_order_count = 0

    def can_edit_vat(self):
        ''' Can't edit `vat` if there is (non draft) issued SO. '''
        can_edit_vat = super(ResPartner, self).can_edit_vat()
        if not can_edit_vat:
            return can_edit_vat
        SaleOrder = self.env['sale.order']
        has_so = SaleOrder.search([
            ('partner_id', 'child_of', self.commercial_partner_id.id),
            ('state', 'in', ['sent', 'sale', 'done'])
        ], limit=1)
        return can_edit_vat and not bool(has_so)

    def action_view_sale_order(self):
        action = self.env['ir.actions.act_window']._for_xml_id('sale.act_res_partner_2_sale_order')
        all_child = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        action["domain"] = [("partner_id", "in", all_child.ids)]
        return action

    def _compute_credit_to_invoice(self):
        # EXTENDS 'account'
        super()._compute_credit_to_invoice()
        domain = [('partner_id', 'in', self.ids), ('state', 'in', ['sale', 'done'])]
        group = self.env['sale.order'].read_group(domain, ['amount_to_invoice'], ['partner_id'])
        for res in group:
            partner = self.browse(res['partner_id'][0])
            partner.credit_to_invoice += res['amount_to_invoice']

    def unlink(self):
        # Unlink draft/cancelled SO so that the partner can be removed from database
        self.env['sale.order'].sudo().search([
            ('state', 'in', ['draft', 'cancel']),
            '|', '|',
            ('partner_id', 'in', self.ids),
            ('partner_invoice_id', 'in', self.ids),
            ('partner_shipping_id', 'in', self.ids),
        ]).unlink()
        return super().unlink()
