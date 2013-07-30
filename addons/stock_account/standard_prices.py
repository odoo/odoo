"""
Keep track of the ``product.product`` standard prices as they are changed.

The ``standard.prices`` model records each ``standard`` or ``average``
``cost_method`` change. For the ``real`` ``cost_method`` it records every
wuants creation.

"""

import openerp

class standard_prices(openerp.osv.orm.Model):

    _name = 'standard.prices'

    _columns = {
        'company_id': openerp.osv.fields.many2one('res.company', required=True),
        'quant_id': openerp.osv.fields.many2one('stock.quant'),
        'product_id': openerp.osv.fields.many2one('product.product'),
        'cost': openerp.osv.fields.float(),
        'date': openerp.osv.fields.date(),
        'reason': openerp.osv.fields.char(),
        # TODO 'origin': openerp.osv.fields.reference(),
    }
