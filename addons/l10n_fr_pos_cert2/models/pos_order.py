#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from functools import partial
import time

from openerp import models, api, _
from openerp.tools import float_is_zero
from openerp.exceptions import UserError


class pos_order(models.Model):
    _inherit = 'pos.order'

    @api.multi
    def action_see_attachments(self):
        self.ensure_one()
        return {
            'name': _('Attachments'),
            'domain': ['&', ('res_model', '=', 'pos.order'), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'context': "{'default_res_model': 'pos.order', 'default_res_id': %d}" % (self.id)
        }

    @api.multi
    def get_l10n_fr_hash(self):
        return self.read(['pos_reference','l10n_fr_hash'])

    @api.model
    def save_ticket(self, order_data, html_ticket):
        order_id = self.env['pos.order'].search([('pos_reference', '=', order_data['name'])], limit=1)
        if order_data.get('l10n_fr_proforma'):
            name = '%s - %s - Proforma.posxml' % (order_id.display_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        else:
            name = '%s - %s - Receipt.posxml' % (order_id.display_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        self.env['ir.attachment'].create({
            'name': name,
            'datas_fname': name,
            'type': 'binary',
            'datas': html_ticket.encode('utf8').encode('base64'),
            'res_model': 'pos.order',
            'res_id': order_id.id,
            'mimetype': 'text/plain',
        })
        return True

    @api.model
    def create_from_ui(self, orders):
        submitted_references = [o['data']['name'] for o in orders]
        existing_orders = self.search_read([('pos_reference', 'in', submitted_references)], ['pos_reference'])
        existing_references = set([o['pos_reference'] for o in existing_orders])
        orders_to_create = [o for o in orders if o['data']['name'] not in existing_references]
        orders_to_update = [o for o in orders if o['data']['name'] in existing_references]

        order_ids = super(pos_order, self).create_from_ui(orders_to_create)

        # duplicated from create_from_ui, but adapted to update existing records instead of creating new ones
        for order in orders_to_update:
            to_invoice = order['to_invoice']
            order = order['data']
            order_id = 0
            for existing_order in existing_orders:
                if existing_order['pos_reference'] == order['name']:
                    order_id = existing_order['id']
                    break
            if order.get('l10n_fr_proforma'):
                self._update_order(order_id, order)
            else:
                if to_invoice:
                    self._match_payment_to_invoice(order)

                self._update_order(order_id, order)
                order_ids.append(order_id)

                # REMOVE ME IN 10.0
                # At this point, The ORM cache contains all pos.order of the session
                # As we'll use a non-stored computed field later, empty the cache
                # ensure not computing this field for the full order list of the session
                # which is a mess with big pos sessions (4000+ tickets)
                self.env['pos.order'].browse([]).env.invalidate_all()
                order = self.env['pos.order'].browse(order_id)
                try:
                    order.signal_workflow('paid')
                except psycopg2.OperationalError:
                    # do not hide transactional errors, the order(s) won't be saved!
                    raise
                except Exception as e:
                    _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

                if to_invoice:
                    order.action_invoice()
                    order.invoice_id.sudo().signal_workflow('invoice_open')

        return order_ids

    @api.model
    def _update_order(self, order_id, order_data):
        prec_acc = self.env['decimal.precision'].precision_get('Account')
        session = self.env['pos.session'].browse(order_data['pos_session_id'])

        if session.state == 'closing_control' or session.state == 'closed':
            session_id = self._get_valid_session(order_data)
            session = self.env['pos.session'].browse(session_id)
            order_data['pos_session_id'] = session_id
        process_line = partial(self.env['pos.order.line']._order_line_fields)
        vals = {
            'lines': [[5, 0, 0]] + [process_line(l) for l in order_data['lines']] if order_data['lines'] else False,
            'session_id': order_data['pos_session_id'],
            'partner_id': order_data['partner_id'] or False,
            'fiscal_position_id': order_data['fiscal_position_id'],
        }
        self.browse(order_id).write(vals)
        journal_ids = set()
        for payments in order_data['statement_ids']:
            if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
                self.add_payment(order_id, self._payment_fields(payments[2]))
            journal_ids.add(payments[2]['journal_id'])

        if session.sequence_number <= order_data['sequence_number']:
            session.write({'sequence_number': order_data['sequence_number'] + 1})
            session.refresh()

        if not float_is_zero(order_data['amount_return'], precision_digits=prec_acc):
            cash_journal = session.cash_journal_id.id
            if not cash_journal:
                # Select for change one of the cash journals used in this payment
                cash_journal_ids = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('id', 'in', list(journal_ids)),
                ], limit=1)
                if not cash_journal_ids:
                    # If none, select for change one of the cash journals of the POS
                    # This is used for example when a customer pays by credit card
                    # an amount higher than total amount of the order and gets cash back
                    cash_journal_ids = [statement.journal_id.id for statement in session.statement_ids
                                        if statement.journal_id.type == 'cash']
                    if not cash_journal_ids:
                        raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
                cash_journal = cash_journal_ids[0]
            self.add_payment(order_id, {
                'amount': -order_data['amount_return'],
                'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_name': _('return'),
                'journal': cash_journal.id,
            })
