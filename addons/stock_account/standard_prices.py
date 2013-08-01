"""
Keep track of the ``product.product`` standard prices as they are changed.

The ``standard.prices`` model records each ``standard`` or ``average``
``cost_method`` change. For the ``real`` ``cost_method`` it records every
wuants creation.

"""

import openerp
from openerp.osv import expression

class standard_prices(openerp.osv.orm.Model):

    _name = 'standard.prices'

    _columns = {
        'company_id': openerp.osv.fields.many2one('res.company',
            required=True),
        'quant_id': openerp.osv.fields.many2one('stock.quant'),
        'product_id': openerp.osv.fields.many2one('product.product'),
        'cost': openerp.osv.fields.float(), # called standard_price on
                                            # product.product
        'datetime': openerp.osv.fields.datetime(),
        'reason': openerp.osv.fields.char(),
        # TODO 'origin': openerp.osv.fields.reference(),
    }

    def _get_default_company(self, cr, uid, context=None):
        if 'force_company' in context:
            return context['force_company']
        else:
            company = self.pool['res.users'].browse(cr, uid, uid,
                context=context).company_id
            return company.id if company else False

    _defaults = {
        'quant_id': False,
        'datetime': openerp.osv.fields.datetime.now,
        'company_id': _get_default_company,
    }

class stock_value(openerp.osv.orm.Model):

    _name = 'stock.value'

    _columns = {
    }

    def _get_value(self, cr, uid, location_id, product_id, moment, context=None):
        # stock_location = self.pool['stock.location']
        stock_move = self.pool['stock.move']
        product_product = self.pool['product.product']

        # Fetch stock moves completed before the requested date.
        domain = expression.AND([
            [('product_id', '=', product_id)],
            [('state', '=', 'done')],
            [('date', '<=', moment)],
        ])
        outgoing_domain = [('location_id', '=', location_id)]
        incoming_domain = [('location_dest_id', '=', location_id)]
        move_ids = stock_move.search(cr, uid,
            expression.AND([
                expression.OR([incoming_domain, outgoing_domain]),
                domain]),
            context=context)

        product = product_product.browse(cr, uid, [product_id],
            context=context)[0]

        if product.cost_method == 'standard':
            quantity = 0
            for move in stock_move.browse(cr, uid, move_ids, context=context):
                if move.location_id == move.location_dest_id:
                    pass
                elif move.location_id == location_id:
                    # outgoing move
                    quantity -= move.product_uom_qty
                elif move.location_dest_id == location_id:
                    quantity += move.product_uom_qty
                    # incoming move
            return quantity * product.standard_price # TODO from standard.prices
        return 123456
