# -*- coding: utf-8 -*-
import datetime

from openerp import http
from openerp.http import request
from openerp import tools
from openerp.tools.translate import _


class website_account(http.Controller):
    @http.route(['/my', '/my/home'], type='http', auth="public", website=True)
    def account(self):
        partner = request.env.user.partner_id
        values = {
            'date': datetime.date.today().strftime('%Y-%m-%d')
        }

        res_sale_order = request.env['sale.order']
        res_invoices = request.env['account.invoice']
        quotations = res_sale_order.search([
            ('partner_id.id', '=', partner.id),
            ('state', 'in', ['sent', 'cancel'])
        ])
        orders = res_sale_order.search([
            ('partner_id.id', '=', partner.id),
            ('state', 'in', ['progress', 'manual', 'shipping_except', 'invoice_except', 'done'])
        ])
        invoices = res_invoices.search([
            ('partner_id.id', '=', partner.id),
            ('state', 'in', ['open', 'paid', 'cancelled'])
        ])

        values.update({
            'quotations': quotations,
            'orders': orders,
            'invoices': invoices
        })

        # get customer sales rep
        if partner.user_id:
            sales_rep = partner.user_id
        else:
            sales_rep = False
        values.update({
            'sales_rep': sales_rep,
            'company': request.website.company_id,
            'user': request.env.user
        })

        return request.website.render("website_portal.account", values)

    @http.route(['/my/orders/<int:order>'], type='http', auth="user", website=True)
    def orders_followup(self, order=None):
        partner = request.env['res.users'].browse(request.uid).partner_id
        domain = [
            ('partner_id.id', '=', partner.id),
            ('state', 'not in', ['draft', 'cancel']),
            ('id', '=', order)
        ]
        order = request.env['sale.order'].search(domain)
        invoiced_lines = request.env['account.invoice.line'].search([('invoice_id', 'in', order.invoice_ids.ids)])
        order_invoice_lines = {il.product_id.id: il.invoice_id for il in invoiced_lines}

        return request.website.render("website_portal.orders_followup", {
            'order': order.sudo(),
            'order_invoice_lines': order_invoice_lines,
        })

    @http.route(['/my/account'], type='http', auth='user', website=True)
    def details(self, redirect=None, **post):
        partner = request.env['res.users'].browse(request.uid).partner_id
        values = {
            'error': {},
            'error_message': []
        }

        if post:
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                post.update({'zip': post.pop('zipcode', '')})
                partner.sudo().write(post)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        values.update({
            'partner': partner,
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'redirect': redirect,
        })

        return request.website.render("website_portal.details", values)

    def details_form_validate(self, data):
        error = dict()
        error_message = []

        mandatory_billing_fields = ["name", "phone", "email", "street2", "city", "country_id"]

        # Validation
        for field_name in mandatory_billing_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # vat validation
        if data.get("vat") and hasattr(request.env["res.partner"], "check_vat"):
            if request.website.company_id.vat_check_vies:
                # force full VIES online check
                check_func = request.env["res.partner"].vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = request.env["res.partner"].simple_vat_check
            vat_country, vat_number = request.env["res.partner"]._split_vat(data.get("vat"))
            if not check_func(vat_country, vat_number): # simple_vat_check
                error["vat"] = 'error'
        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        return error, error_message
