# -*- coding: utf-8 -*-
import werkzeug

from openerp import http
from openerp.http import request
from openerp import tools
from openerp.tools.translate import _


class website_payment(http.Controller):
    @http.route(['/my/payment_method'], type='http', auth="user", website=True)
    def payment_method(self):
        acquirers = list(request.env['payment.acquirer'].search([('website_published', '=', True), ('registration_view_template_id', '!=', False)]))
        partner = request.env.user.partner_id
        payment_methods = partner.payment_method_ids
        values = {
            'pms': payment_methods,
            'acquirers': acquirers
        }
        for acquirer in acquirers:
            acquirer.form = acquirer.sudo()._registration_render(request.env.user.partner_id.id, {'error': {}, 'error_message': [], 'return_url': '/my/payment_method', 'json': False, 'bootstrap_formatting': True})[0]
        return request.website.render("website_payment.pay_methods", values)

    @http.route(['/website_payment/delete/'], method=['POST'], type='http', auth="user", website=True)
    def delete(self, delete_pm_id=None):
        if delete_pm_id:
            pay_meth = request.env['payment.method'].browse(int(delete_pm_id))
            pay_meth.unlink()
        return request.redirect('/my/payment_method')
