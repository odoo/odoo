from osv import osv, fields

class travel_hostel(osv.osv):
	_name = 'travel.hostel'
	_inherit = 'res.partner'
	_table = 'res_partner'
	_columns = {
		'rooms_id': fields.one2many('travel.room', 'hostel_id', 'Rooms'),
		'quality': fields.char('Quality', size=16),
	}
travel_hostel()

class travel_airport(osv.osv):
	_name = 'travel.airport'
	_columns = {
		'name': fields.char('Airport name', size=16),
		'city': fields.char('City', size=16),
		'country': fields.many2one('res.country', 'Country')
	}
travel_airport()

class travel_room(osv.osv):
	_name = 'travel.room'
	_inherit = 'product.product'
	_table = 'product_product'
	_columns = {
		'beds': fields.integer('Nbr of Beds'),
		'view': fields.selection([('sea','Sea'),('street','Street')], 'Room View'),
		'hostel_id': fields.many2one('travel.hostel', 'Hostel'),
	}
travel_room()
class travel_flight(osv.osv):
	_name = 'travel.flight'
	_inherit = 'product.product'
	_table = 'product_product'
	_columns = {
		'partner_id': fields.many2one('res.partner', 'PArtner'),
		'date': fields.datetime('Departure Date'),
		'airport_from': fields.many2one('travel.airport', 'Airport Departure'),
		'airport_to': fields.many2one('travel.airport', 'Airport Arrival'),
	}
travel_flight()

