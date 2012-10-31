from osv import osv, fields

class lunch_order_order(osv.Model):
    """ lunch order meal """
    _name = 'lunch.order.order'
    _description = 'Wizard to order a meal'

    def order(self,cr,uid,ids,context=None):
        order_lines_ref = self.pool.get('lunch.order.line')
        active_ids =  context.get('active_ids', [])
        for order_line in order_lines_ref.browse(cr,uid,active_ids,context=context):
            if order_line.state!='confirmed' and order_line.state!='ordered':
                order_lines_ref.write(cr,uid,[order_line.id],{'state':'ordered'},context)
        return {}