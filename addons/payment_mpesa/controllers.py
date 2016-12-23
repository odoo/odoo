# -*- coding: utf-8 -*-
#from openerp import http
import openerp
import openerp.addons.website_sale.controllers.main
import logging
import pprint
import werkzeug
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)


class mpesaController(http.Controller):
    _accept_url = '/payment/mpesa/feedback'
    #_logger.info('*******************************88888888888888888888888888888888888888888888*************************88')
    mandatory_mpesa_fields = ["confirm_code"]
    @http.route([
        '/payment/mpesa/feedback',
    ], type='http', auth='public', website=True )
    def mpesa_form_feedback(self, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning form_feedback with post data %s', pprint.pformat(post))
	if len(post.get('confirm_code')) < 9:
	   order_obj = request.registry.get('sale.order')
	   order_obj._set_mpesa_data(post)
           _logger.info('SSSSSSSSSSSSSSSSSSSSSSSSS REDIRECTING COZ OF ERRORR with POST  as: %s', pprint.pformat(post))
	   return request.redirect("/shop/payment")

        request.registry['payment.transaction'].form_feedback(cr, uid, post, 'mpesa', context)
        return werkzeug.utils.redirect(post.pop('return_url', '/'))



#class website_sale(openerp.addons.website_sale.controllers.main.website_sale):
#
#    @http.route(['/shop/payment'], type='http', auth="public", website=True)
#    def payment(self, **post):
#        cr, uid, context = request.cr, request.uid, request.context
#        order = request.website.sale_get_order(context=context)
#        _logger.info('SSSSSSSSSSSSSSSSSSSSSSSSS MPESA INHERITED PAYMENT CONTROLLER  is: %s', pprint.pformat(order))
#        _logger.info('SSSSSSSSSSSSSSSSSSSSSSSSS REDIRECTED POST as : %s', pprint.pformat(post))
#
#        res = super(website_sale, self).payment(**post)
#        return res
#
