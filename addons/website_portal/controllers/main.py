# -*- coding: utf-8 -*-
import datetime

from openerp import http
from openerp.http import request
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval


class website_account(http.Controller):
    @http.route(['/account'], type='http', auth="public", website=True)
    def account(self):
        partner = request.env.user.partner_id
        values = {
            'date': datetime.date.today().strftime('%Y-%m-%d')
        }

        res_sale_order = request.env['sale.order']
        res_invoices = request.env['account.invoice']
        quotations = res_sale_order.search([
            ('partner_id.id', 'in', [partner.id, partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ])
        orders = res_sale_order.search([
            ('partner_id.id', 'in', [partner.id, partner.commercial_partner_id.id]),
            ('state', 'in', ['progress', 'manual', 'shipping_except', 'invoice_except', 'done'])
        ])
        invoices = res_invoices.search([
            ('partner_id.id', 'in', [partner.id, partner.commercial_partner_id.id]),
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
        elif partner.commercial_partner_id and partner.commercial_partner_id.user_id:
            sales_rep = partner.commercial_partner_id.user_id
        else:
            sales_rep = False
        values.update({
            'sales_rep': sales_rep,
            'company': request.website.company_id,
            'user': request.env.user
        })

        return request.website.render("website_portal.account", values)

    @http.route(['/account/orders/<int:order>'], type='http', auth="user", website=True)
    def orders_followup(self, order=None):
        partner = request.env['res.users'].browse(request.uid).partner_id
        domain = [
            ('partner_id.id', 'in', [partner.id, partner.commercial_partner_id.id]),
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

    @http.route(['/account/details', '/account/details/<int:partner_id>', '/account/details/new'], type='http', auth='user', website=True)
    def details(self, partner_id=None, **post):
        user = request.env['res.users'].browse(request.uid)
        if partner_id:
            partner = request.env['res.partner'].browse(partner_id)
            if partner.parent_id != user.partner_id:
                return request.render("website.404")
        else:
            partner = user.partner_id
        values = {
            'error': {},
            'error_message': []
        }
        params = request.env['ir.config_parameter']

        if post:
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                if bool(post.get('is_new')):
                    post.update({
                        'parent_id': partner.id,
                        'zip': post.pop('zipcode', ''),
                        'type': 'delivery',
                    })
                    request.env['res.partner'].sudo().create(post)
                else:
                    post.update({'zip': post.pop('zipcode', '')})
                    partner.sudo().write(post)
                return request.redirect('/account/details')

        countries = request.env['res.country'].sudo().search([])
        us_id = request.env['res.country'].sudo().search([('name', '=', 'United States')]).id
        states = request.env['res.country.state'].sudo().search([])
        
        values.update({
            'partner': partner,
            'countries': countries,
            'is_child': partner != user.partner_id,
            'is_new': 'new' in request.httprequest.path,
            'contacts': partner.child_ids.filtered(lambda p: p.type == 'contact'),
            'addresses': partner.child_ids.filtered(lambda p: p.type == 'delivery'),
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'validate': safe_eval(params.sudo().get_param('website_portal.address_validation', default="False")),
            'mandatory_validation': safe_eval(params.sudo().get_param('website_portal.mandatory_validation', default="False")),
            'us_id': us_id,
        })

        return request.website.render("website_portal.details", values)

    def details_form_validate(self, data):
        error = dict()
        error_message = []

        mandatory_billing_fields = ["name", "phone", "email", "street2", "city", "country_id"]
        optional_billing_fields = ["street", "state_id", "vat", "vat_subjected", "zip"]

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

    @http.route(['/account/details/shipping/<int:shipping_id>'], type='http', auth='user', website=True)
    def shipping(self, shipping_id, **post):
        user = request.env['res.users'].browse(request.uid)
        partner = user.partner_id

        shipping = request.env['res.partner'].browse(shipping_id)

        partner.sudo().default_shipping_id = shipping

        return request.redirect('/account/details')

    @http.route(['/account/details/<int:partner_id>/remove'], type='http', auth='user', website=True)
    def remove(self, partner_id, **post):
        user = request.env['res.users'].browse(request.uid)
        partner = request.env['res.partner'].browse(partner_id)

        if partner.parent_id == user.partner_id and partner.type == 'delivery':
            partner.sudo().write({'active': False})
            if user.partner_id.default_shipping_id == partner:
                user.partner_id.sudo().default_shipping_id = False

        return request.redirect('/account/details')

    @http.route(['/account/details/validate'], type='json', auth='user', method=['POST'], website=True)
    def validate(self, **post):
        params = post.get('params')
        state_id = params.get('state_id')
        if state_id:
            state = request.env['res.country.state'].browse(int(state_id))
        address = {
            'street': params.get('street2'),  # magical street/company implementation in website_sale
            'city': params.get('city'),
            'zip': params.get('zipcode'),
            'state': state.code if state_id else 'XX',
        }
        return request.env['res.partner'].sudo().validate_address(address) 
