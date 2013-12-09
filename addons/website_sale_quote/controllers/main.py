import random
import uuid
import simplejson

import werkzeug.exceptions

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website

class sale_quote(http.Controller):

    def get_quote(self, token):
        order_pool = request.registry.get('sale.order')
        order_id = order_pool.search(request.cr, SUPERUSER_ID, [('access_token', '=', token)], context=request.context)
        return order_id

    @website.route(['/quote/<token>'], type='http', auth="public")
    def view(self, token=None, **post):
        values = {}
        order_pool = request.registry.get('sale.order')
        quotation = order_pool.browse(request.cr, SUPERUSER_ID, self.get_quote(token))[0]
        render_template = 'website_sale_quote.so_quotation'
        values.update({
            'quotation' : quotation,
        })
        return request.website.render(render_template, values)

    @website.route(['/quote/<token>/accept'], type='http', auth="public")
    def accept(self, token=None , **post):
        values = {}
        quotation = request.registry.get('sale.order').write(request.cr, SUPERUSER_ID, self.get_quote(token), {'state': 'manual'})
        return request.redirect("/quote/%s" % token)

    @website.route(['/quote/<token>/decline'], type='http', auth="public")
    def decline(self, token=None , **post):
        values = {}
        quotation = request.registry.get('sale.order').write(request.cr, SUPERUSER_ID, self.get_quote(token), {'state': 'cancel'})
        return request.redirect("/quote/%s" % token)

    @website.route(['/quote/<token>/post'], type='http', auth="public")
    def post(self, token=None, **post):
        values = {}
        if post.get('new_message'):
            request.session.body = post.get('new_message')
        if 'body' in request.session and request.session.body:
            request.registry.get('sale.order').message_post(request.cr, SUPERUSER_ID, self.get_quote(token),
                    body=request.session.body,
                    type='email',
                    subtype='mt_comment',
                )
            request.session.body = False
        return request.redirect("/quote/%s" % token)

    @website.route(['/quote/update_line'], type='json', auth="public")
    def update(self, line_id=None, qty=None, remove=False,unlink=False,**post):
        if unlink:
            request.registry.get('sale.order.line').unlink(request.cr, SUPERUSER_ID,[int(line_id)], context=request.context)
        else:
            val = self._update_order_line(line_id=int(line_id), number=(remove and -1 or 1), qty=int(qty))
#            order = request.registry['website'].get_current_order(request.cr, request.uid, context=request.context)
        return {}
    
    def _update_order_line(self,line_id, number,qty):
        qty += number
        request.registry.get('sale.order.line').write(request.cr, SUPERUSER_ID, [int(line_id)], {'product_uom_qty':(qty)}, context=request.context)
        return qty
