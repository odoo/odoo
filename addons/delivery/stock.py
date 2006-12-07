import netsvc
from osv import fields,osv


# Overloaded stock_picking to manage carriers :
class stock_picking(osv.osv):
	_name = "stock.picking"
	_description = "Picking list"
        _inherit = 'stock.picking'
	_columns = {
 		'carrier_id':fields.many2one("delivery.carrier","Carrier"),
		'volume': fields.float('Volume'),
		'weight': fields.float('Weight'),

	}



stock_picking()
