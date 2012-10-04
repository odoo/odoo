from osv import osv, fields

class lunch_validation(osv.Model):
	""" lunch validation """
	_name = 'lunch.validation'
	_description = 'lunch validation for order'

	def confirm(self,cr,uid,ids,context=None):
		#confirm one or more order.line, update order status and create new cashmove
		cashmove_ref = self.pool.get('lunch.cashmove')
		order_lines_ref = self.pool.get('lunch.order.line')
		orders_ref = self.pool.get('lunch.order')
		order_ids = context.get('active_ids', [])

		for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
			if order.state!='confirmed':
				new_id = cashmove_ref.create(cr,uid,{'user_id': order.user_id.id, 'amount':0 - order.price,'description':order.product.name, 'order_id':order.id, 'state':'order', 'date':order.date})
				order_lines_ref.write(cr,uid,[order.id],{'cashmove':[('0',new_id)], 'state':'confirmed'},context)
		for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
			isconfirmed = True
			for product in order.order_id.products:
				if product.state == 'new':
					isconfirmed = False
				if product.state == 'cancelled':
					isconfirmed = False
					orders_ref.write(cr,uid,[order.order_id.id],{'state':'partially'},context)
			if isconfirmed == True:
				orders_ref.write(cr,uid,[order.order_id.id],{'state':'confirmed'},context)
		return {}