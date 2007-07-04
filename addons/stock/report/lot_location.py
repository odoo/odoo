import pooler
import time
from report import report_sxw

class lot_location(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(lot_location, self).__init__(cr, uid, name, context)
		self.localcontext.update({
			'time': time,
			'process':self.process,
		})

	def process(self,location_id):
		res = {}
		location_obj = pooler.get_pool(self.cr.dbname).get('stock.location')
		product_obj = pooler.get_pool(self.cr.dbname).get('product.product')

		res['location_name'] = pooler.get_pool(self.cr.dbname).get('stock.location').read(self.cr, self.uid, [location_id],['name'])[0]['name']

		prod_info = location_obj._product_get(self.cr, self.uid, location_id)

		res['product'] = []
		for prod in product_obj.browse(self.cr, self.uid, prod_info.keys()):
			if prod_info[prod.id]:
				res['product'].append({'prod_name': prod.name, 'prod_qty': prod_info[prod.id]})
		if not res['product']:
			res['product'].append({'prod_name': '', 'prod_qty': ''})
		location_child = location_obj.read(self.cr, self.uid, [location_id], ['child_ids'])
		list=[]
		list.append(res)
		for child_id in location_child[0]['child_ids']:
				list.extend(self.process(child_id))

		return list

report_sxw.report_sxw('report.lot.location', 'stock.location', 'addons/stock/report/lot_location.rml', parser=lot_location)

