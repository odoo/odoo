# from odoo import http
# from odoo.http import request


# class UserProfileController(http.Controller):

#     @http.route('/user/orders/status', type='http', auth='user', website=True)
#     def order_status(self, **kw):
#         user = request.env.user
#         sale_orders = request.env['sale.order'].sudo().search([('partner_id', '=', user.partner_id.id), ('state', 'in', ['sale'])])
#         data = [{
#             'name': so.name,
#             'quantity': sum(so.order_line.mapped('product_uom_qty')),
#             'status': 'Pending Shipment' if not so.picking_ids else 'Shipped',
#             'image_url': so.order_line[0].product_id.image_1920 and "/web/image/product.product/{}/image_1920".format(so.order_line[0].product_id.id) or '',
#         } for so in sale_orders]
#         return request.render('multi_vendor_marketplace.user_order_status', {'orders': data})

#     @http.route('/user/orders/history', type='http', auth='user', website=True)
#     def order_history(self, **kw):
#         user = request.env.user
#         sale_orders = request.env['sale.order'].sudo().search([('partner_id', '=', user.partner_id.id)], order='date_order desc')
#         data = [{
#             'name': so.name,
#             'quantity': sum(so.order_line.mapped('product_uom_qty')),
#             'status': 'Delivered' if all(p.state == 'done' for p in so.picking_ids) else 'In Transit',
#             'image_url': so.order_line[0].product_id.image_1920 and "/web/image/product.product/{}/image_1920".format(so.order_line[0].product_id.id) or '',
#             'date_order': so.date_order.date(),
#             'time_order': so.date_order.time().strftime('%H:%M')
#         } for so in sale_orders]
#         return request.render('multi_vendor_marketplace.user_order_history', {'orders': data})

#     @http.route('/user/orders/returns', type='http', auth='user', website=True)
#     def order_returns(self, **kw):
#         user = request.env.user
#         return_orders = request.env['stock.return.picking'].sudo().search([('partner_id', '=', user.partner_id.id)], order='create_date desc')
#         data = [{
#             'name': ro.name,
#             'quantity': 1,  # or use line info if available
#             'status': 'Return Requested',
#             'image_url': '',
#             'date_return': ro.create_date.date(),
#             'time_return': ro.create_date.time().strftime('%H:%M')
#         } for ro in return_orders]
#         return request.render('multi_vendor_marketplace.user_order_returns', {'returns': data})
