# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.osv import expression


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        SaleOrder = request.env['sale.order']
        quotation_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ])
        order_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done'])
        ])

        values.update({
            'quotation_count': quotation_count,
            'order_count': order_count,
        })
        return values

    #
    # Quotations and Sales Orders
    #

    @http.route(['/my/quotes', '/my/quotes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_quotes(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        quotation_count = SaleOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/quotes",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        quotations = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_quotes_history'] = quotations.ids[:100]

        values.update({
            'date': date_begin,
            'quotations': quotations.sudo(),
            'page_name': 'quote',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/quotes',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("sale.portal_my_quotations", values)

    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done'])
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        order_count = SaleOrder.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("sale.portal_my_orders", values)

    def _compute_values(self, order_sudo, pdf, access_token, message, now):
        days = 0
        if order_sudo.validity_date:
            days = (fields.Date.from_string(order_sudo.validity_date) - fields.Date.from_string(fields.Date.today())).days + 1
        transaction = order_sudo.get_portal_last_transaction()

        values = {
            'quotation': order_sudo,
            'message': message and int(message) or False,
            'order_valid': (not order_sudo.validity_date) or (now <= order_sudo.validity_date),
            'days_valid': days,
            'action': request.env.ref('sale.action_quotations').id,
            'no_breadcrumbs': request.env.user.partner_id.commercial_partner_id not in order_sudo.message_partner_ids,
            'tx_id': transaction.id if transaction else False,
            'tx_state': transaction.state if transaction else False,
            'payment_tx': transaction,
            'tx_post_msg': transaction.acquirer_id.post_msg if transaction else False,
            'need_payment': order_sudo.invoice_status == 'to invoice' and transaction.state in ['draft', 'cancel'],
            'token': access_token,
            'return_url': '/shop/payment/validate',
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
        }

        if order_sudo.has_to_be_paid() or values['need_payment']:
            domain = expression.AND([
                ['&', ('website_published', '=', True), ('company_id', '=', order_sudo.company_id.id)],
                ['|', ('specific_countries', '=', False), ('country_ids', 'in', [order_sudo.partner_id.country_id.id])]
            ])
            acquirers = request.env['payment.acquirer'].sudo().search(domain)

            values['form_acquirers'] = [acq for acq in acquirers if acq.payment_flow == 'form' and acq.view_template_id]
            values['s2s_acquirers'] = [acq for acq in acquirers if acq.payment_flow == 's2s' and acq.registration_view_template_id]
            values['pms'] = request.env['payment.token'].search(
                [('partner_id', '=', order_sudo.partner_id.id),
                ('acquirer_id', 'in', [acq.id for acq in values['s2s_acquirers']])])

        history = request.session.get('my_quotes_history', [])
        values.update(get_records_pager(history, order_sudo))
        return values

    @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
    def portal_order_page(self, order_id, pdf=None, access_token=None, message=False, **kw):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except AccessError:
            return request.redirect('/my')

        if pdf:
            pdf = request.env.ref('sale.report_web_quote').sudo().with_context(set_viewport_size=True).render_qweb_pdf([order_sudo.id])[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        now = fields.Date.today()
        if access_token:
            Order = request.env['sale.order'].sudo().search([('id', '=', order_id), ('access_token', '=', access_token)])
        else:
            Order = request.env['sale.order'].search([('id', '=', order_id)])
        # Log only once a day
        if Order and request.session.get('view_quote_%s' % Order.id) != now and request.env.user.share and access_token:
            request.session['view_quote_%s' % Order.id] = now
            body = _('Quotation viewed by customer')
            _message_post_helper(res_model='sale.order', res_id=Order.id, message=body, token=Order.access_token, message_type='notification', subtype="mail.mt_note", partner_ids=Order.user_id.sudo().partner_id.ids)
        if not Order:
            return request.redirect('/my')

        # Token or not, sudo the order, since portal user has not access on
        # taxes, required to compute the total_amout of SO.
        order_sudo = Order.sudo()
        values = self._compute_values(order_sudo, pdf, access_token, message, now)
        return request.render('sale.so_quotation', values)

    @http.route(['/my/orders/pdf/<int:order_id>'], type='http', auth="public", website=True)
    def portal_order_report(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token)
        except AccessError:
            return request.redirect('/my')

        # print report as sudo, since it require access to taxes, payment term, ... and portal
        # does not have those access rights.
        pdf = request.env.ref('sale.action_report_saleorder').sudo().render_qweb_pdf([order_sudo.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    def _portal_quote_user_can_accept(self, order):
        return order.company_id.portal_confirmation_sign or order.company_id.portal_confirmation_pay

    @http.route(['/my/quotes/accept'], type='json', auth="public", website=True)
    def portal_quote_accept(self, res_id, access_token=None, partner_name=None, signature=None):
        try:
            order_sudo = self._document_check_access('sale.order', res_id, access_token=access_token)
        except AccessError:
            return {'error': _('Invalid order')}
        if order_sudo.state != 'sent':
            return {'error': _('Order is not in a state requiring customer validation.')}

        if not self._portal_quote_user_can_accept(order_sudo):
            return {'error': _('Operation not allowed')}
        if not signature:
            return {'error': _('Signature is missing.')}

        success_message = _('Your order has been signed but still needs to be paid to be confirmed.')

        if not order_sudo.has_to_be_paid():
            order_sudo.action_confirm()
            success_message = _('Your order has been confirmed.')

        order_sudo.signature = signature
        order_sudo.signed_by = partner_name

        pdf = request.env.ref('sale.action_report_saleorder').sudo().render_qweb_pdf([order_sudo.id])[0]
        _message_post_helper(
            res_model='sale.order',
            res_id=order_sudo.id,
            message=_('Order signed by %s') % (partner_name,),
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            **({'token': access_token} if access_token else {}))

        return {
            'success': success_message,
            'redirect_url': '/my/orders/%s?%s' % (order_sudo.id, access_token and 'access_token=%s' % order_sudo.access_token or ''),
        }
