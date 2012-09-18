from osv import osv, fields

class Car (osv.Model):

	_name = ’hr_fleet_management.car’

	_columns = {
		’name’ : fields.char(’Car name’, 128, required = True),
		’description’ : fields.text(’Description’),
	}
