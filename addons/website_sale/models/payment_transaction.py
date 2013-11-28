# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class PaymentTransaction(orm.Model):
    _inherit = 'payment.transaction'

    _columns = {
        # link with the sale order
        'sale_order_id': fields.many2one('sale.order', 'Sale Order'),
    }
