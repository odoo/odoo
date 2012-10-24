from osv import osv, fields

class lunch_cancel(osv.Model):
	""" lunch cancel """
	_name = 'lunch.cancel'
	_description = 'cancel lunch order'

	def cancel(self,cr,uid,ids,context=None):
		#confirm one or more order.line, update order status and create new cashmove
		cashmove_ref = self.pool.get('lunch.cashmove')
		order_lines_ref = self.pool.get('lunch.order.line')
		orders_ref = self.pool.get('lunch.order')
		order_ids = context.get('active_ids', [])

		for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
			order_lines_ref.write(cr,uid,[order.id],{'state':'cancelled'},context)
			for cash in order.cashmove:
				cashmove_ref.unlink(cr,uid,cash.id,context)
		for order in order_lines_ref.browse(cr,uid,order_ids,context=context):
			hasconfirmed = False
			hasnew = False
			for product in order.order_id.products:
				if product.state=='confirmed':
					hasconfirmed= True
				if product.state=='new':
					hasnew= True
			if hasnew == False:
				if hasconfirmed == False:
					orders_ref.write(cr,uid,[order.order_id.id],{'state':'cancelled'},context)
					return {}
			orders_ref.write(cr,uid,[order.order_id.id],{'state':'partially'},context)
		return {}
