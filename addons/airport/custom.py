from osv import osv, fields

class airport_airport(osv.osv):
	_name = 'airport.airport'
	_columns = {
		'name': fields.char('Airport name', size=16),
		'city': fields.char('City', size=16),
		'country_id': fields.many2one('res.country', 'Country'),
		'lines': fields.many2many('airport.airport', 'airport_airport_lines_rel', 'source','destination', 'Flight lines')
	}
airport_airport()

class airport_flight(osv.osv):
	_name = 'airport.flight'
	_inherit = 'product.product'
	_table = 'product_product'
	_columns = {
		'date': fields.datetime('Departure Date'),
		'partner_id': fields.many2one('res.partner', 'Customer'),
		'airport_from': fields.many2one('airport.airport', 'Airport Departure'),
		'airport_to': fields.many2one('airport.airport', 'Airport Arrival'),
	}
airport_flight()

