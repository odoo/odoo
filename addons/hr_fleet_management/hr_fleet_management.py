# -*- coding: utf-8 -*-
from osv import osv, fields

class fleet_vehicle_model (osv.Model):

	_name = 'fleet.vehicle.model'
	_description = '...'

	_columns = {
		'name' : fields.char('Car name', 128, required = True),
	}
	
class fleet_vehicle(osv.Model):
	_name = 'fleet.vehicle'
	_description = 'Fleet Vehicle'

	_columns = {
		'name' : fields.char('Name', size=32, required=True),
		'model_id' : fields.many2one('fleet.vehicle.model','Model', required=True),
	}
