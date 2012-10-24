from osv import osv, fields

class res_partner (osv.Model):
	_inherit = 'res.partner'	
	_columns = {
		'supplier_lunch': fields.boolean('Lunch Supplier'),
	}