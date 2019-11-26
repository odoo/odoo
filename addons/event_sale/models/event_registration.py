# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_is_zero


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    # in addition to origin generic fields, add real relational fields to correctly
    # handle attendees linked to sales orders and their lines
    # TDE FIXME: maybe add an onchange on sale_order_id + origin
    sale_order_id = fields.Many2one('sale.order', string='Source Sales Order', ondelete='cascade')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line', ondelete='cascade')
    campaign_id = fields.Many2one('utm.campaign', 'Campaign', related="sale_order_id.campaign_id", store=True)
    source_id = fields.Many2one('utm.source', 'Source', related="sale_order_id.source_id", store=True)
    medium_id = fields.Many2one('utm.medium', 'Medium', related="sale_order_id.medium_id", store=True)

    def _check_auto_confirmation(self):
        res = super(EventRegistration, self)._check_auto_confirmation()
        if res:
            orders = self.env['sale.order'].search([('state', '=', 'draft'), ('id', 'in', self.mapped('sale_order_id').ids)], limit=1)
            if orders:
                res = False
        return res

    @api.model
    def create(self, vals):
        if vals.get('sale_order_line_id'):
            so_line_vals = self._synchronize_so_line_values(
                self.env['sale.order.line'].browse(vals['sale_order_line_id'])
            )
            vals.update(so_line_vals)
        res = super(EventRegistration, self).create(vals)
        if res.origin or res.sale_order_id:
            res.message_post_with_view(
                'mail.message_origin_link',
                values={'self': res, 'origin': res.sale_order_id},
                subtype_id=self.env.ref('mail.mt_note').id)
        return res

    def write(self, vals):
        if vals.get('sale_order_line_id'):
            so_line_vals = self._synchronize_so_line_values(
                self.env['sale.order.line'].browse(vals['sale_order_line_id'])
            )
            vals.update(so_line_vals)
        return super(EventRegistration, self).write(vals)

    def _synchronize_so_line_values(self, so_line):
        if so_line:
            return {
                'partner_id': so_line.order_id.partner_id.id,
                'event_id': so_line.event_id.id,
                'event_ticket_id': so_line.event_ticket_id.id,
                'origin': so_line.order_id.name,
                'sale_order_id': so_line.order_id.id,
                'sale_order_line_id': so_line.id,
            }
        return {}

    def _get_registration_summary(self):
        res = super(EventRegistration, self)._get_registration_summary()
        order = self.sale_order_id.sudo()
        order_line = self.sale_order_line_id.sudo()
        has_to_pay = False
        if not order or float_is_zero(order_line.price_total, precision_digits=order.currency_id.rounding):
            payment_status = _('Free')
        elif not order.invoice_ids or any(invoice.payment_state != 'paid' for invoice in order.invoice_ids):
            payment_status = _('To pay')
            has_to_pay = True
        else:
            payment_status = _('Paid')
        res.update({
            'payment_status': payment_status,
            'has_to_pay': has_to_pay
        })
        return res
