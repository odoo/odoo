"""
Keep track of the ``product.product`` standard prices as they are changed.

The ``standard.prices`` model records each ``standard`` or ``average``
``cost_method`` change. For the ``real`` ``cost_method`` it records every
wuants creation.

"""

import openerp
from openerp.osv import expression

class price_history(openerp.osv.orm.Model):

    _name = 'price.history'

    _columns = {
        'company_id': openerp.osv.fields.many2one('res.company',
            required=True),
        'product_id': openerp.osv.fields.many2one('product.product'), # required = True
        'datetime': openerp.osv.fields.datetime(),
        'cost': openerp.osv.fields.float(), # called standard_price on
                                            # product.product
        'reason': openerp.osv.fields.char(),
        # TODO 'origin': openerp.osv.fields.reference(),
        'quant_id': openerp.osv.fields.many2one('stock.quant'),
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

class quant_history(openerp.osv.orm.Model):

    _name = 'quant.history'

    _auto = False

    _columns = {
        'id': openerp.osv.fields.integer(),
        'move_id': openerp.osv.fields.many2one('stock.move'),
        'quant_id': openerp.osv.fields.many2one('stock.quant'),
        'location_id': openerp.osv.fields.many2one('stock.location'),
        'product_id': openerp.osv.fields.many2one('product.product'),
        'quantity': openerp.osv.fields.integer(),
        'date': openerp.osv.fields.datetime(),
        'cost': openerp.osv.fields.float(),
    }

    def init(self, cr):
        openerp.tools.drop_view_if_exists(cr, 'stock_valuation')
        cr.execute("""
            create or replace view quant_history as (
                select
                    history.id as id,
                    history.move_id as move_id,
                    history.quant_id as quant_id,
		    stock_quant.location_id as location_id,
		    stock_quant.product_id as product_id,
		    stock_quant.qty as quantity,
                    stock_move.date as date,
                    (select price_history.cost from price_history where price_history.datetime < stock_move.date order by price_history.datetime asc limit 1) as cost
                from
                    stock_quant_move_rel as history
                left join
                    stock_move on stock_move.id = history.move_id
                left join
                    stock_quant on stock_quant.id = history.quant_id
            )""")
