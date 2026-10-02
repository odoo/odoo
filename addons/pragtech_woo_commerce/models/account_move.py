# -*- coding: utf-8 -*-

from woocommerce import API
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    woo_id = fields.Char('WooCommerce ID')
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)

    def import_woo_refund(self, instance_id, order):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        url = "orders/%s/refunds" % order.woo_id
        try:
            response = wcapi.get(url)
        except Exception as error:
            raise UserError(_("Please check your connection and try again"))

        if response.status_code == 200 and response.content:
            parsed_data = response.json()
            for rec in parsed_data:
                credit_note = self.search(
                    [('id', '=', order.invoice_ids.ids), ('move_type', '=', 'out_refund')])
                if credit_note:
                    raise ValidationError('Already credit note created')
                if order.state == 'draft':
                    order.action_confirm()
                    move = order._create_invoices(
                        grouped=False, final=False, date=None)
                    move.write({'state': 'posted'})
                    order.write({'invoice_status': 'invoiced'})
                    move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move",
                                                                                   active_ids=order.invoice_ids.ids).create(
                        {
                            'date': datetime.datetime.today().strftime('%Y-%m-%d'),
                            'reason': 'no reason',
                            'journal_id': order.invoice_ids.journal_id.id, })
                    credit_note = move_reversal.reverse_moves()
                    if credit_note:
                        credit_move_id = self.env['account.move'].browse(credit_note.get('res_id'))
                        credit_move_id.action_post()
                elif order.state == 'sale':
                    if order.invoice_ids.ids:
                        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move",
                                                                                       active_ids=order.invoice_ids.ids).create(
                            {
                                'date': datetime.datetime.today().strftime('%Y-%m-%d'),
                                'reason': 'no reason',
                                'journal_id': order.invoice_ids.journal_id.id, })
                        credit_note = move_reversal.reverse_moves()
                        if credit_note:
                            credit_move_id = self.env['account.move'].browse(credit_note.get('res_id'))
                            credit_move_id.action_post()
                    else:
                        move = order._create_invoices(
                            grouped=False, final=False, date=None)
                        move.write({'state': 'posted'})
                        order.write({'invoice_status': 'invoiced'})
                        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move",
                                                                                       active_ids=order.invoice_ids.ids).create(
                            {
                                'date': datetime.datetime.today().strftime('%Y-%m-%d'),
                                'reason': 'no reason',
                                'journal_id': order.invoice_ids.journal_id.id, })
                        credit_note = move_reversal.reverse_moves()
                        if credit_note:
                            credit_move_id = self.env['account.move'].browse(credit_note.get('res_id'))
                            credit_move_id.action_post()
                else:
                    pass


                # credit_move = self.sudo().search([('woo_id', '=', rec.get('id'))])
                #
                # if not credit_move:
                #     for picking in order.picking_ids:
                #         picking.action_cancel()
                #     move = order._create_invoices(grouped=False, final=False, date=None)
                #     move.sudo().write({
                #         'is_exported': True,
                #         'woo_id': rec.get('id'),
                #         'woo_instance_id': instance_id.id,
                #     })
                #     move.action_switch_invoice_into_refund_credit_note()
                #     if move.state == 'draft':
                #         move.action_post()
