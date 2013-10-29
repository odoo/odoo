"""
Keep track of the ``product.product`` standard prices as they are changed.

The ``standard.prices`` model records each ``standard`` or ``average``
``cost_method`` change. For the ``real`` ``cost_method`` it records every
wuants creation.

"""

from openerp import tools
from openerp.osv import fields, osv

class price_history(osv.osv):

    _name = 'price.history'
    _rec_name = 'datetime'

    _columns = {
        'company_id': fields.many2one('res.company', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'datetime': fields.datetime('Historization Time'),
        'cost': fields.float('Historized Cost'),
        'reason': fields.char('Reason'),
        # TODO 'origin': openerp.osv.fields.reference(),
        #'quant_id': openerp.osv.fields.many2one('stock.quant'),
    }

    def _get_default_company(self, cr, uid, context=None):
        if 'force_company' in context:
            return context['force_company']
        else:
            company = self.pool['res.users'].browse(cr, uid, uid,
                context=context).company_id
            return company.id if company else False

    _defaults = {
        #'quant_id': False,
        'datetime': fields.datetime.now,
        'company_id': _get_default_company,
    }


class stock_history(osv.osv):
    _name = 'stock.history'
    _auto = False

    _columns = {
        'move_id': fields.many2one('stock.move', 'Stock Move'),
        #'quant_id': fields.many2one('stock.quant'),
        'location_id': fields.many2one('stock.location', 'Location'),
        'product_id': fields.many2one('product.product', 'Product'),
        'quantity': fields.integer('Quantity'),
        'date': fields.datetime('Date'),
        'cost': fields.float('Value'),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_history')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_history AS (
                SELECT
                    stock_move.id AS id,
                    stock_move.id AS move_id,
                    stock_move.location_id AS location_id,
                    stock_move.product_id AS product_id,
                    stock_move.product_qty AS quantity,
                    stock_move.date AS date,
                    CASE
                      WHEN ir_property.value_text <> 'real'
                        THEN (SELECT price_history.cost FROM price_history WHERE price_history.datetime <= stock_move.date AND price_history.product_id = stock_move.product_id ORDER BY price_history.datetime ASC limit 1)
                      ELSE stock_move.price_unit
                    END AS cost
                FROM
                    stock_move
                LEFT JOIN
                    product_product ON product_product.id = stock_move.product_id
                LEFT JOIN
                    product_template ON product_template.id = product_product.product_tmpl_id
                LEFT JOIN
                    ir_property ON (ir_property.name = 'cost_method' and ir_property.res_id = 'product.template,' || product_template.id::text)
                WHERE stock_move.state = 'done'
            )""")
