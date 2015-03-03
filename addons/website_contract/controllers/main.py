# -*- coding: utf-8 -*-
import hashlib
import werkzeug

from openerp.addons.website_portal.controllers.main import website_account
from openerp import http
from openerp.http import request
from openerp import tools
from openerp.tools import plaintext2html
from openerp.tools.translate import _


class website_contract(website_account):
    @http.route(['/account'], type='http', auth="user", website=True)
    def account(self):
        """ Add contract details to main account page """
        response = super(website_contract, self).account()
        partner = request.env.user.partner_id
        res_accounts = request.env['account.analytic.account']
        cust_accounts = res_accounts.search([
            '&',
            '|',
            ('partner_id.id', '=', partner.id),
            ('partner_id.id', '=', partner.commercial_partner_id.id),
            ('state', '!=', 'cancelled')
            ])
        response.qcontext.update({'cust_accounts': cust_accounts})

        return response

    @http.route(['/account/contract/<int:account_id>'], type='http', auth="user", website=True)
    def contract(self, account_id):
        res_accounts = request.env['account.analytic.account']
        account_cust = res_accounts.browse(account_id)
        user = request.env['res.users'].browse(request.uid)
        values = {
            'account': account_cust,
            'user': user,
        }
        return request.website.render("website_contract.contract", values)

    @http.route(['/account/contract/<int:account_id>/<string:uuid>'], type='http', auth="public", website=True)
    def contract_with_hash(self, account_id, uuid):
        """ Public-accessible url to share the contract directly with the customer, without portal access """
        res_accounts = request.env['account.analytic.account']
        account_cust = res_accounts.sudo().browse(account_id)
        user = request.env['res.users'].browse(request.uid)
        if account_cust.uuid == uuid:
            values = {
                'account': account_cust,
                'user': user,
            }
            return request.website.render("website_contract.contract", values)
        return request.render("website.404")

    @http.route(['/account/contract/<int:account_id>/change'], type='http', auth="user", website=True)
    def change_contract(self, account_id, **post):
        res_accounts = request.env['account.analytic.account']
        account_cust = res_accounts.browse(account_id)
        if account_cust.state == 'close':
            return request.redirect('/account/contract/'+str(account_id))
        user = request.env['res.users'].browse(request.uid)
        if post.get('new_template_id'):
            new_template_id = int(post.get('new_template_id'))
            new_template = res_accounts.browse(new_template_id)
            periods = {'daily': 'Day(s)', 'weekly': 'Week(s)', 'monthly': 'Month(s)', 'yearly': 'Year(s)'}
            msg_body = _("""
                <div>Contract template changed</div>
                <div>&nbsp;&nbsp;&bull; <b>Old Template</b>: """)+account_cust.sudo().template_id.name+_("""</div>
                <div>&nbsp;&nbsp;&bull; <b>Old Recurring Price</b>: """)+str(account_cust.recurring_total)+_("""</div>
                <div>&nbsp;&nbsp;&bull; <b>Old Invoicing Period</b>: """)+str(account_cust.recurring_interval)+' '+str(periods[account_cust.recurring_rule_type])+"""</div><br/>"""
            account_cust.sudo().change_subscription(new_template_id)
            msg_body += _("""
                <div>&nbsp;&nbsp;&bull; <b>New Template</b>: """)+account_cust.sudo().template_id.name+_("""</div>
                <div>&nbsp;&nbsp;&bull; <b>New Recurring Price</b>: """)+str(account_cust.recurring_total)+_("""</div>
                <div>&nbsp;&nbsp;&bull; <b>New Invoicing Period</b>: """)+str(account_cust.recurring_interval)+' '+str(periods[account_cust.recurring_rule_type])+"""</div>"""
            # price options are about to change and are not propagated to existing sale order: reset the SO
            order = request.website.sudo().sale_get_order()
            if order:
                order.reset_project_id()
            account_cust.message_post(body=msg_body)
            return request.redirect('/account/contract/'+str(account_cust.id))
        account_templates = res_accounts.sudo().search([
            ('type', '=', 'template'),
            ('parent_id', '=', account_cust.template_id.sudo().parent_id.id)
            ])
        values = {
            'account': account_cust,
            'account_templates': account_templates,
            'user': user,
        }
        return request.website.render("website_contract.change_template", values)

    @http.route(['/account/contract/<int:account_id>/close'], type='http', methods=["POST"], auth="user", website=True)
    def close_account(self, account_id, **post):
        account_cust = request.env['account.analytic.account'].browse(account_id)
        if account_cust.sudo().template_id.user_closable and post.get('confirm_close'):
            account_cust.set_close()
        return request.redirect('/account')

    @http.route(['/account/contract/<int:account_id>/add_option'], type='http', methods=["POST"], auth="user", website=True)
    def add_option(self, account_id, **post):
        account_cust = request.env['account.analytic.account'].browse(account_id)
        new_option_id = int(post.get('new_option_id'))
        new_option = request.env['account.analytic.invoice.line.option'].sudo().browse(new_option_id)
        if not new_option.price_unit or not new_option.price_unit*account_cust.partial_recurring_invoice_ratio():
            account_cust.sudo().add_option(new_option_id)
            account_cust.message_post(body=_("""
            <div>Option added by customer</div>
            <div>&nbsp;&nbsp;&bull; <b>Option</b>: """)+new_option.product_id.name_template+_("""</div>
            <div>&nbsp;&nbsp;&bull; <b>Price</b>: """)+str(new_option.price_unit)+_("""</div>
            <div>&nbsp;&nbsp;&bull; <b>Sale Order</b>: None</div>"""))
        return request.redirect('/account/contract/'+str(account_id))

    @http.route(['/account/contract/<int:account_id>/remove_option'], type='http', methods=["POST"], auth="public", website=True)
    def remove_option(self, account_id, **post):
        remove_option_id = int(post.get('remove_option_id'))
        remove_option = request.env['account.analytic.invoice.line.option'].browse(remove_option_id)
        account_cust = request.env['account.analytic.account'].browse(account_id)
        if remove_option.portal_access != "both" and not request.env['res.users'].has_group('base.group_sale_salesman'):
            return request.render("website.403")
        account_cust.sudo().remove_option(remove_option_id)
        account_cust.message_post(body=_("""
            <div>Option removed by customer</div>
            <div>&nbsp;&nbsp;&bull; <b>Option</b>: """)+remove_option.product_id.sudo().name_template+_("""</div>
            <div>&nbsp;&nbsp;&bull; <b>Price</b>: """)+str(remove_option.price_unit)+"""</div>""")
        return request.redirect('/account/contract/'+str(account_id))

    @http.route(['/account/contract/<int:account_id>/pay_option'], type='http', methods=["POST"], auth="public", website=True)
    def pay_option(self, account_id, **post):
        order = request.website.sale_get_order(force_create=True)
        order.set_project_id(account_id)
        new_option_id = int(post.get('new_option_id'))
        new_option = request.env['account.analytic.invoice.line.option'].sudo().browse(new_option_id)
        account_cust = request.env['account.analytic.account'].browse(account_id)
        account_cust.sudo().partial_invoice_line(order, new_option)

        return request.redirect("/shop/cart")
