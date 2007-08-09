import netsvc
from osv import fields,osv


# Overloaded sale_order to manage carriers :
class sale_order(osv.osv):
	_name = "sale.order"
	_inherit = 'sale.order'	
	_description = "Sale Order"

	_columns = {
 		'carrier_id':fields.many2one("delivery.carrier","Delivery method", help="Complete this field if you plan to invoice the shipping based on packings made."),
	}

	def onchange_partner_id(self, cr, uid, ids, part):
		result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part)
		if part:
			dtype = self.pool.get('res.partner').browse(cr, uid, part).property_delivery_carrier.id
			result['value']['carrier_id'] = dtype
		return result

	def action_ship_create(self, cr, uid, ids, *args):
		result = super(sale_order, self).action_ship_create(cr, uid, ids, *args)
		for order in self.browse(cr, uid, ids, context={}):
			pids = [ x.id for x in order.picking_ids]
			self.pool.get('stock.picking').write(cr, uid, pids, {
				'carrier_id':order.carrier_id.id,
			})
		return result
sale_order()




