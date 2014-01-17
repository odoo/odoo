# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
import werkzeug


class sale_quote(http.Controller):

    @website.route(["/quote/<int:order_id>/<token>"], type='http', auth="public")
    def view(self, order_id, token, **post):
        # use SUPERUSER_ID allow to access/view order for public user
        order = request.registry.get('sale.order').browse(request.cr, SUPERUSER_ID, order_id)
        assert token == order.access_token, 'Access denied, wrong token!'
        # TODO: if not order.template_id: return to the URL of the portal view of SO
        values = {
            'quotation': order,
            'new_post' : request.httprequest.session.get('new_post',False)
        }
        return request.website.render('website_quotation.so_quotation', values)

    @website.route(['/quote/<int:order_id>/<token>/accept'], type='http', auth="public")
    def accept(self, order_id, token, **post):
        order = request.registry.get('sale.order').browse(request.cr, SUPERUSER_ID, order_id)
        assert token == order.access_token, 'Access denied, wrong token!'
        request.registry.get('sale.order').write(request.cr, request.uid, [order_id], {'state': 'manual'})
        return request.redirect("/quote/%s/%s" % (order_id, token))

    @website.route(['/quote/<int:order_id>/<token>/decline'], type='http', auth="public")
    def decline(self, order_id, token, **post):
        message = post.get('decline_message')
        request.registry.get('sale.order').write(request.cr, request.uid, [order_id], {'state': 'cancel'})
        if message:
            self.message_post(message, order_id)
        return werkzeug.utils.redirect("/quote/%s/%s" % (order_id, token))

    @website.route(['/quote/<int:order_id>/<token>/post'], type='http', auth="public")
    def post(self, order_id, token, **post):
        # use SUPERUSER_ID allow to access/view order for public user
        order_obj = request.registry.get('sale.order')
        order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
        message = post.get('comment')
        assert token == order.access_token, 'Access denied, wrong token!'
        if message:
            self.message_post(message, order_id)
            request.httprequest.session['new_post'] = True
        return werkzeug.utils.redirect("/quote/%s/%s" % (order_id, token))

    def message_post(self , message, order_id):
        request.session.body =  message
        cr, uid, context = request.cr, request.uid, request.context
        if 'body' in request.session and request.session.body:
            request.registry.get('sale.order').message_post(cr, uid, order_id,
                    body=request.session.body,
                    type='comment',
                    subtype='mt_comment',
                    context=context,
                )
            request.session.body = False
        return True

    @website.route(['/quote/<int:order_id>/<token>/close'], type='http', auth="public")
    def close(self, order_id, token, **post):
        """ close an alert message when click on 'X' and set session new_post as False"""
        order_obj = request.registry.get('sale.order')
        order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
        assert token == order.access_token, 'Access denied, wrong token!'
        request.httprequest.session['new_post'] = False
        return werkzeug.utils.redirect("/quote/%s/%s" % (order_id, token))

    @website.route(['/quote/update_line'], type='json', auth="public")
    def update(self, line_id=None, remove=False, unlink=False, order_id=None, token=None, **post):
        order = request.registry.get('sale.order').browse(request.cr, SUPERUSER_ID, int(order_id))
        assert token == order.access_token, 'Access denied, wrong token!'
        if unlink:
            request.registry.get('sale.order.line').unlink(request.cr, SUPERUSER_ID, [int(line_id)], context=request.context)
            return False
        val = self._update_order_line(line_id=int(line_id), number=(remove and -1 or 1))
        return [str(val), str(order.amount_total)]

    def _update_order_line(self, line_id, number):
        order_line_obj = request.registry.get('sale.order.line')
        order_line_val = order_line_obj.read(request.cr, SUPERUSER_ID, [line_id], [], context=request.context)[0]
        quantity = order_line_val['product_uom_qty'] + number
        order_line_obj.write(request.cr, SUPERUSER_ID, [line_id], {'product_uom_qty': (quantity)}, context=request.context)
        return quantity

    @website.route(["/template/<model('sale.quote.template'):quote>"], type='http', auth="public")
    def template_view(self, quote, **post):
        values = {
            'template': quote,
        }
        return request.website.render('website_quotation.so_template', values)
        
    @website.route(["/quote/add_line/<int:option_id>/<int:order_id>/<token>"], type='http', auth="public")
    def add(self, option_id, order_id, token, **post):
        vals = {}
        order = request.registry.get('sale.order').browse(request.cr, SUPERUSER_ID, order_id)
        assert token == order.access_token, 'Access denied, wrong token!'
        option_obj = request.registry.get('sale.option.line')
        option = option_obj.browse(request.cr, SUPERUSER_ID, option_id)
        vals.update({
            'price_unit': option.price_unit,
            'website_description': option.website_description,
            'name': option.name,
            'order_id': order.id,
            'product_id' : option.product_id.id,
            'product_uom_qty': option.quantity,
            'product_uom_id': option.uom_id.id,
            'discount': option.discount,
            'is_optional': True,
        })
        line = request.registry.get('sale.order.line').create(request.cr, SUPERUSER_ID, vals, context=request.context)
        option_obj.write(request.cr, SUPERUSER_ID, [option.id], {'line_id': line}, context=request.context)
        return werkzeug.utils.redirect("/quote/%s/%s" % (order.id, token))


