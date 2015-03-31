# -*- coding: utf-8 -*-
import werkzeug

from openerp import http
from openerp.http import request
from openerp import tools
from openerp.tools.translate import _


class website_payment(http.Controller):
    @http.route(['/payment'], type='http', auth="user", website=True)
    def account(self, **post):
        acquirers = request.env['payment.acquirer'].search([('website_published', '=', True)])
        values = {
            'acquirers': list({'id': acquirer.id, 'name': acquirer.name, 'template': acquirer.s2s_render(request.env.user.partner_id.id, {'return_success': "/account"})[0]} for acquirer in acquirers),
            'error': {},
            'error_message': []
        }
        
        if post:
            acquirer_id = post.get('acquirer_id')
            acquirer = request.env['payment.acquirer'].browse(acquirer_id)
            redirect = acquirer.s2s_process(post, success_redirect="/account", fail_redirect="/account")
            return request.redirect(redirect)

        return request.website.render("website_payment.cc_form", values)

    @http.route(['/account/payment_method'], type='http', auth="user", website=True)
    def payment_method(self):
        acquirers = list(request.env['payment.acquirer'].search([('website_published', '=', True), ('s2s_support', '=', True)]))
        partner = request.env.user.partner_id
        payment_methods = partner.payment_method_ids
        values = {
            'pms': payment_methods,
            'acquirers': acquirers
        }
        for acquirer in acquirers:
            acquirer.form = acquirer.s2s_render(request.env.user.partner_id.id, {'error': {}, 'error_message': [], 'return_url': '/account/payment_method', 'json': False, 'bootstrap_formatting': True})[0]
        return request.website.render("website_payment.pay_methods", values)

    @http.route(['/account/payment_method/delete/'], type='http', auth="user", website=True)
    def delete(self, delete_pm_id=None):
        if delete_pm_id:
            pay_meth = request.env['payment.method'].browse(int(delete_pm_id))
            pay_meth.active = False
        return request.redirect('/account/payment_method')
