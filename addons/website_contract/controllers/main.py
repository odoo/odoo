# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from openerp import http
from openerp.http import request
from openerp.tools.translate import _

from openerp.addons.website_portal.controllers.main import website_account


class website_account(website_account):
    @http.route(['/account'], type='http', auth="user", website=True)
    def account(self):
        """ Add contract details to main account page """
        response = super(website_account, self).account()
        partner = request.env.user.partner_id
        account_res = request.env['account.analytic.account']
        accounts = account_res.search([
            ('partner_id.id', 'in', [partner.id, partner.commercial_partner_id.id]),
            ('state', '!=', 'cancelled'),
            ('contract_type', '=', 'subscription')
        ])
        response.qcontext.update({'accounts': accounts})

        return response


class website_contract(http.Controller):
    @http.route(['/account/contract/<int:account_id>/',
                 '/account/contract/<int:account_id>/<string:uuid>'], type='http', auth="public", website=True)
    def contract(self, account_id, uuid='', message='', message_class=''):
        request.env['res.users'].browse(request.uid).has_group('base.group_sale_salesman')
        account_res = request.env['account.analytic.account']
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                return request.render("website.404")
            if request.uid == account.partner_id.user_id.id:
                account = account_res.browse(account_id)
        else:
            account = account_res.browse(account_id)

        acquirers = list(request.env['payment.acquirer'].search([('website_published', '=', True), ('s2s_support', '=', True)]))
        acc_pm = account.payment_method_id
        part_pms = account.partner_id.payment_method_ids
        inactive_options = account.sudo().recurring_inactive_lines
        display_close = account.template_id.sudo().user_closable and account.state != 'close'
        active_plan = account.template_id.sudo()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[account.recurring_rule_type]: account.recurring_interval})
        limit_date = datetime.datetime.strptime(account.recurring_next_date, '%Y-%m-%d') + invoicing_period
        allow_reopen = datetime.datetime.today() < limit_date
        dummy, action = request.env['ir.model.data'].get_object_reference('sale_contract', 'action_account_analytic_overdue_all')
        account_templates = account_res.sudo().search([
            ('type', '=', 'template'),
            ('parent_id', '=', account.template_id.sudo().parent_id.id),
            ('user_selectable', '=', True),
            ('id', '!=', active_plan.id),
            ('state', '=', 'open')
        ])
        values = {
            'account': account,
            'display_close': display_close,
            'close_reasons': request.env['account.analytic.close.reason'].search([]),
            'allow_reopen': allow_reopen,
            'inactive_options': inactive_options,
            'active_plan': active_plan,
            'user': request.env.user,
            'acquirers': acquirers,
            'acc_pm': acc_pm,
            'part_pms': part_pms,
            'is_salesman': request.env['res.users'].sudo(request.uid).has_group('base.group_sale_salesman'),
            'action': action,
            'message': message,
            'message_class': message_class,
            'display_change_plan': len(account_templates) > 0,
            'pricelist': account.pricelist_id
        }
        render_context = {
            'json': True,
            'submit_class': 'btn btn-primary btn-sm mb8 mt8 pull-right',
            'submit_txt': 'Save and Pay',
            'bootstrap_formatting': True
        }
        render_context = dict(values.items() + render_context.items())
        for acquirer in acquirers:
            acquirer.form = acquirer.s2s_render(account.partner_id.id, render_context)[0]
        return request.website.render("website_contract.contract", values)

    payment_succes_msg = 'message=Thank you, your payment has been validated.&message_class=alert-success'
    payment_fail_msg = 'message=There was an error with your payment, please try with another payment method or contact us.&message_class=alert-danger'

    @http.route(['/account/contract/payment/<int:account_id>/',
                 '/account/contract/payment/<int:account_id>/<string:uuid>'], type='http', auth="public", methods=['POST'], website=True)
    def payment(self, account_id, uuid=None, **post):
        account_res = request.env['account.analytic.account']
        invoice_res = request.env['account.invoice']
        get_param = ''
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                return request.render("website.404")
        else:
            account = account_res.browse(account_id)

        # no change
        if int(post.get('pay_meth'), 0) > 0:
            account.payment_method_id = int(post['pay_meth'])

        # we can't call _recurring_invoice because we'd miss 3DS, redoing the whole payment here
        payment_method = account.payment_method_id
        if payment_method:
            invoice_values = account_res.sudo()._prepare_invoice(account)
            new_invoice = invoice_res.sudo().create(invoice_values)
            new_invoice.check_tax_lines(request.env['account.invoice.tax'].compute(new_invoice))
            tx = account.sudo()._do_payment(payment_method, new_invoice)[0]
            if tx.html_3ds:
                return tx.html_3ds
            account.sudo().reconcile_pending_transaction(tx, new_invoice)
            get_param = self.payment_succes_msg if tx.state == 'done' else self.payment_fail_msg

        return request.redirect('/account/contract/%s/%s?%s' % (account.id, account.uuid, get_param))

    # 3DS controllers
    # transaction began as s2s but we receive a form reply
    @http.route(['/account/contract/<int:account_id>/payment/<int:tx_id>/accept/',
                 '/account/contract/<int:account_id>/payment/<int:tx_id>/decline/',
                 '/account/contract/<int:account_id>/payment/<int:tx_id>/exception/'], type='http', auth="public", website=True)
    def payment_accept(self, account_id, tx_id, **kwargs):
        account_res = request.env['account.analytic.account']
        tx_res = request.env['payment.transaction']

        account = account_res.sudo().browse(account_id)
        tx = tx_res.sudo().browse(tx_id)

        tx.form_feedback(kwargs, tx.acquirer_id.provider)
        account.reconcile_pending_transaction(tx, tx.invoice_id)
        get_param = self.payment_succes_msg if tx.state == 'done' else self.payment_fail_msg

        return request.redirect('/account/contract/%s/%s?%s' % (account.id, account.uuid, get_param))

    @http.route(['/account/contract/<int:account_id>/change'], type='http', auth="public", website=True)
    def change_contract(self, account_id, uuid=None, **post):
        account_res = request.env['account.analytic.account']
        account = account_res.sudo().browse(account_id)
        if uuid != account.uuid:
            return request.render("website.404")
        if account.state == 'close':
            return request.redirect('/account/contract/'+str(account_id))
        if post.get('new_template_id'):
            new_template_id = int(post.get('new_template_id'))
            new_template = account_res.browse(new_template_id)
            periods = {'daily': 'Day(s)', 'weekly': 'Week(s)', 'monthly': 'Month(s)', 'yearly': 'Year(s)'}
            msg_before = [account.sudo().template_id.name,
                          str(account.recurring_total),
                          str(account.recurring_interval) + ' ' + str(periods[account.recurring_rule_type])]
            account.sudo().change_subscription(new_template_id)
            msg_after = [account.sudo().template_id.name,
                         str(account.recurring_total),
                         str(account.recurring_interval) + ' ' + str(periods[account.recurring_rule_type])]
            msg_body = ("<div>&nbsp;&nbsp;&bull; <b>" + _('Template') + "</b>: " + msg_before[0] + " &rarr; " + msg_after[0] + "</div>" +
                        "<div>&nbsp;&nbsp;&bull; <b>" + _('Recurring Price') + "</b>: " + msg_before[1] + " &rarr; " + msg_after[1] + "</div>" +
                        "<div>&nbsp;&nbsp;&bull; <b>" + _('Invoicing Period') + "</b>: " + msg_before[2] + " &rarr; " + msg_after[2] + "</div>")
            # price options are about to change and are not propagated to existing sale order: reset the SO
            order = request.website.sudo().sale_get_order()
            if order:
                order.reset_project_id()
            account.message_post(body=msg_body)
            return request.redirect('/account/contract/'+str(account.id)+'/'+str(account.uuid))
        account_templates = account_res.sudo().search([
            ('type', '=', 'template'),
            ('parent_id', '=', account.template_id.sudo().parent_id.id),
            ('state', '=', 'open')
        ])
        values = {
            'account': account,
            'pricelist': account.pricelist_id,
            'active_template': account.template_id,
            'inactive_templates': account_templates,
            'user': request.env.user,
        }
        return request.website.render("website_contract.change_template", values)

    @http.route(['/account/contract/<int:account_id>/close'], type='http', methods=["POST"], auth="public", website=True)
    def close_account(self, account_id, uuid=None, **post):
        account_res = request.env['account.analytic.account']

        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                return request.render("website.404")
        else:
            account = account_res.browse(account_id)

        if account.sudo().template_id.user_closable:
            close_reason = request.env['account.analytic.close.reason'].browse(int(post.get('close_reason_id')))
            account.close_reason_id = close_reason
            if post.get('closing_text'):
                account.message_post(_('Closing text : ') + post.get('closing_text'))
            account.set_close()
            account.date = datetime.date.today().strftime('%Y-%m-%d')
        return request.redirect('/account')

    @http.route(['/account/contract/<int:account_id>/add_option'], type='http', methods=["POST"], auth="public", website=True)
    def add_option(self, account_id, uuid=None, **post):
        option_res = request.env['account.analytic.invoice.line.option']
        account_res = request.env['account.analytic.account']
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                return request.render("website.404")
        else:
            account = account_res.browse(account_id)
        new_option_id = int(post.get('new_option_id'))
        new_option = option_res.sudo().browse(new_option_id)
        if not new_option.price_unit or not new_option.price_unit * account.partial_recurring_invoice_ratio():
            account.sudo().add_option(new_option_id)
            account.message_post(body=_("""
            <div>Option added by customer</div>
            <div>&nbsp;&nbsp;&bull; <b>Option</b>: """) + new_option.product_id.name_template + _("""</div>
            <div>&nbsp;&nbsp;&bull; <b>Price</b>: """) + str(new_option.price_unit) + _("""</div>
            <div>&nbsp;&nbsp;&bull; <b>Sale Order</b>: None</div>"""))
        return request.redirect('/account/contract/%s/%s' % (account.id, account.uuid))

    @http.route(['/account/contract/<int:account_id>/remove_option'], type='http', methods=["POST"], auth="public", website=True)
    def remove_option(self, account_id, uuid=None, **post):
        remove_option_id = int(post.get('remove_option_id'))
        option_res = request.env['account.analytic.invoice.line.option']
        account_res = request.env['account.analytic.account']
        if uuid:
            remove_option = option_res.sudo().browse(remove_option_id)
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                return request.render("website.404")
        else:
            remove_option = option_res.browse(remove_option_id)
            account = account_res.browse(account_id)
        if remove_option.portal_access != "both" and not request.env.user.has_group('base.group_sale_salesman'):
            return request.render("website.403")
        account.sudo().remove_option(remove_option_id)
        account.message_post(body=_("""
            <div>Option removed by customer</div>
            <div>&nbsp;&nbsp;&bull; <b>Option</b>: """) + remove_option.product_id.sudo().name_template+_("""</div>
            <div>&nbsp;&nbsp;&bull; <b>Price</b>: """) + str(remove_option.price_unit)+"""</div>""")
        return request.redirect('/account/contract/%s/%s' % (account.id, account.uuid))

    @http.route(['/account/contract/<int:account_id>/pay_option'], type='http', methods=["POST"], auth="public", website=True)
    def pay_option(self, account_id, **post):
        order = request.website.sale_get_order(force_create=True)
        order.set_project_id(account_id)
        new_option_id = int(post.get('new_option_id'))
        new_option = request.env['account.analytic.invoice.line.option'].sudo().browse(new_option_id)
        account = request.env['account.analytic.account'].browse(account_id)
        account.sudo().partial_invoice_line(order, new_option)

        return request.redirect("/shop/cart")

    @http.route(['/account/template/<int:template_id>'], type='http', auth="user", website=True)
    def view_template(self, template_id):
        account_res = request.env['account.analytic.account']
        dummy, action = request.env['ir.model.data'].get_object_reference('sale_contract', 'template_of_subscription_contract_action')
        values = {
            'template': account_res.browse(template_id),
            'action': action
        }
        return request.website.render('website_contract.preview_template', values)

