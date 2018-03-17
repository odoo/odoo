# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    folio_id = fields.Many2one('hotel.folio', 'Folio Number')


class HotelFolio(models.Model):

    _inherit = 'hotel.folio'
    _order = 'folio_pos_order_ids desc'

    folio_pos_order_ids = fields.Many2many('pos.order', 'hotel_pos_rel',
                                           'hotel_folio_id', 'pos_id',
                                           'Orders', readonly=True, copy=False)

    @api.multi
    def action_invoice_create(self, grouped=False, states=None):
        state = ['confirmed', 'done']
        folio = super(HotelFolio)
        invoice_id = folio.action_invoice_create(grouped=False, states=state)
        for line in self:
            for pos_order in line.folio_pos_order_ids:
                pos_order.write({'invoice_id': invoice_id})
                pos_order.action_invoice_state()
        return invoice_id

    @api.multi
    def action_cancel(self):
        '''
        @param self: object pointer
        '''
        for folio in self:
            for rec in folio.folio_pos_order_ids:
                rec.write({'state': 'cancel'})
        return super(HotelFolio, self).action_cancel()


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        for rec in self:
            invoice_id = rec._context.get('active_id', False)
            folio = self.env['hotel.folio'].search([('hotel_invoice_id', '=',
                                                     invoice_id)], limit=1)
            for order in folio.folio_pos_order_ids:
                amount = order.amount_total - order.amount_paid
                data = rec.read()[0]
                data['journal'] = rec.journal_id.id
                data['amount'] = amount
                if amount != 0.0:
                    order.add_payment(data)
                if order.test_paid():
                    order.action_pos_order_paid()
        return res
