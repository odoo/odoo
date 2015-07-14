# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.osv import orm, fields


class PaymentTransaction(orm.Model):
    _inherit = 'payment.transaction'

    _columns = {
        # link with the sale order
        'sale_order_id': fields.many2one('sale.order', 'Sale Order'),
    }

    def form_feedback(self, cr, uid, data, acquirer_name, context=None):
        """ Override to confirm the sale order, if defined, and if the transaction
        is done. """
        tx = None
        res = super(PaymentTransaction, self).form_feedback(cr, uid, data, acquirer_name, context=context)

        # fetch the tx, check its state, confirm the potential SO
        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            tx = getattr(self, tx_find_method_name)(cr, uid, data, context=context)
        if tx and tx.state == 'done' and tx.sale_order_id and tx.sale_order_id.state in ['draft', 'sent']:
            self.pool['sale.order'].action_button_confirm(cr, SUPERUSER_ID, [tx.sale_order_id.id], context=dict(context, send_email=True))
        elif tx and tx.state not in ['cancel'] and tx.sale_order_id and tx.sale_order_id.state in ['draft']:
            self.pool['sale.order'].force_quotation_send(cr, SUPERUSER_ID, [tx.sale_order_id.id], context=context)

        return res
