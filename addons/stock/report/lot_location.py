import pooler
import time
from report import report_sxw

class lot_location(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(lot_location, self).__init__(cr, uid, name, context)
		self.ret_list=[]
		print "Init Repot::",
		self.localcontext.update({
			'time': time,
			'process':self.process,

		})
		#self.context = context
	def preprocess(self, objects, data, ids):
		print "Records for process ............",ids;
		super(lot_location, self).preprocess(objects, data, ids)

	def process(self,location_id):
		ret_dict = {'location_name':''};
		location_name = pooler.get_pool(self.cr.dbname).get('stock.location').read(self.cr, self.uid, [location_id],['name'])
		if location_name:
			ret_dict['location_name']= str(location_name[0]['name'])
		prod_info = pooler.get_pool(self.cr.dbname).get('stock.location')._product_get(self.cr, self.uid, location_id)

		pro_list = [];
		for prod_id in prod_info.keys():
			pro_dict={}
			if prod_info[prod_id] != 0.0:
				prod_name = pooler.get_pool(self.cr.dbname).get('product.product').read(self.cr, self.uid, [prod_id], ['name'])
				if prod_name:
					pro_dict['prod_name'] =  prod_name[0]['name']
					pro_dict['prod_qty'] =  str(prod_info[prod_id])
					pro_list.append(pro_dict)
			else:
				pro_dict = {'prod_name':'','prod_qty':''};
		pro_list.append(pro_dict)
		ret_dict['product'] = pro_list
		if prod_info:
			self.ret_list.append(ret_dict)
			location_child = pooler.get_pool(self.cr.dbname).get('stock.location').read(self.cr, self.uid, [location_id], ['child_ids'])
			for child_id in location_child[0]['child_ids']:
				self.process(child_id)

		return self.ret_list

#		for location_id in self.ids:
#			process(location_id, 0,[])
#		print "Last ret::",self.ret_list
#		return self.ret_list

report_sxw.report_sxw('report.lot.location', 'stock.location', 'addons/stock/report/lot_location.rml', parser=lot_location)

