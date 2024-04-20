# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import time
from collections import OrderedDict
from datetime import datetime

from odoo import http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request, Response
from odoo.tools import image_process, escape_psql
from odoo.tools.translate import _
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager

VERIFIED_SESSION_DURATION_S = 60 * 60  # 1 hour
MAX_SIZE_UPLOADED_BILL_B = 1024 * 1024 * 1024 * 10  # 10 MiB
MAX_CREATED_BANK_RECORDS = 20


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        PurchaseOrder = request.env['purchase.order']
        if 'rfq_count' in counters:
            values['rfq_count'] = PurchaseOrder.search_count([
                ('state', 'in', ['sent'])
            ]) if PurchaseOrder.check_access_rights('read', raise_exception=False) else 0
        if 'purchase_count' in counters:
            values['purchase_count'] = PurchaseOrder.search_count([
                ('state', 'in', ['purchase', 'done', 'cancel'])
            ]) if PurchaseOrder.check_access_rights('read', raise_exception=False) else 0
        return values

    def _get_purchase_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }

    def _render_portal(self, template, page, date_begin, date_end, sortby, filterby, domain, searchbar_filters, default_filter, url, history, page_name, key):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = self._get_purchase_searchbar_sortings()
        # default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if searchbar_filters:
            # default filter
            if not filterby:
                filterby = default_filter
            domain += searchbar_filters[filterby]['domain']

        # count for pager
        count = PurchaseOrder.search_count(domain)

        # make pager
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=count,
            page=page,
            step=self._items_per_page
        )

        # search the purchase orders to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session[history] = orders.ids[:100]

        values.update({
            'date': date_begin,
            key: orders,
            'page_name': page_name,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': url,
        })
        return request.render(template, values)

    def _session_is_verified(self, company, data_owner_partner, session=None):
        """Verifies that uploading bills and managing bank accounts is enabled in the settings and that logged_in_partner
        is in possession of a verified session to access data belonging to data_owner_partner.

        :param company: the res.company in which data is being accessed.
        :param data_owner_partner: the partner whose data is being accessed.
        :param session: provide an alternative session store, only meant for tests.
        :returns: a boolean indicating if the session is valid.
        """
        if not session:
            session = request.session

        if company.allow_vendor_bill_upload and \
           data_owner_partner.id == session.get('purchase-vendor-verified-partner-id') and \
           int(time.time()) < session.get('purchase-vendor-verified-until', 0):
            return True

        session.pop('purchase-vendor-verified-partner-id', None)
        session.pop('purchase-vendor-verified-until', None)
        return False

    def _session_check(self, company, data_owner_partner):
        """This function should be called in every route that accesses or modifies confidential vendor-related data (e.g.
        bank accounts, cancelling of bills, etc.)

        :param company: the res.company in which data is being accessed.
        :param data_owner_partner: the partner whose data is being accessed.
        :raise AccessError: if there is no verified session.
        """
        if not self._session_is_verified(company, data_owner_partner):
            raise AccessError(_('Please verify your email address.'))

    def _purchase_order_get_page_view_values(self, order, access_token, **kwargs):
        #
        def resize_to_48(source):
            if not source:
                source = request.env['ir.binary']._placeholder()
            else:
                source = base64.b64decode(source)
            return base64.b64encode(image_process(source, size=(48, 48)))

        is_logged_in_as_customer = request.env.user.partner_id.commercial_partner_id == order.partner_id.commercial_partner_id
        values = {
            'order': order,
            'resize_to_48': resize_to_48,
            'report_type': 'html',
            'bank_accounts': request.env['res.partner.bank'].sudo().search([('partner_id', '=', request.env.user.partner_id.commercial_partner_id.id)]),
            'my_bank_account_link': '/my/bank_account?purchase_order_id=%s' % order.id,
            'is_logged_in_user_customer': is_logged_in_as_customer,
            'verified_session': self._session_is_verified(request.env.company, order.partner_id.commercial_partner_id),
        }
        if order.state in ('sent'):
            history = 'my_rfqs_history'
        else:
            history = 'my_purchases_history'
        return self._get_page_view_values(order, access_token, values, history, False, **kwargs)

    @http.route(['/my/rfq', '/my/rfq/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests_for_quotation(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        return self._render_portal(
            "purchase.portal_my_purchase_rfqs",
            page, date_begin, date_end, sortby, filterby,
            [('state', '=', 'sent')],
            {},
            None,
            "/my/rfq",
            'my_rfqs_history',
            'rfq',
            'rfqs'
        )

    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        return self._render_portal(
            "purchase.portal_my_purchase_orders",
            page, date_begin, date_end, sortby, filterby,
            [],
            {
                'all': {'label': _('All'), 'domain': [('state', 'in', ['purchase', 'done', 'cancel'])]},
                'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
                'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
                'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
            },
            'all',
            "/my/purchase",
            'my_purchases_history',
            'purchase',
            'orders'
        )

    def _validate_and_read_vendor_attachment(self, attachment_file):
        """Makes sure attachments uploaded by vendors are reasonably-sized PDFs.

        :params attachment_file: the POSTed werkzeug.datastructures.FileStorage.
        :return: a tuple containing the filename and bytes."""
        data = attachment_file.read()
        if len(data) > MAX_SIZE_UPLOADED_BILL_B:
            raise ValidationError(_('The uploaded file is too large.'))

        if attachment_file.content_type != 'application/pdf':
            raise ValidationError(_('The uploaded file is not a PDF.'))

        return attachment_file.filename, data

    def _process_uploaded_bill(self, order_sudo, bank_account_id, uploaded_pdf):
        """Creates a vendor bill on the portal user's behalf. The uploaded PDF is attached and the chosen bank account
        is set.

        :param order_sudo: a sudo'd purchase order on which the bill was uploaded.
        :param bank_account_id: the chosen bank account.
        :param uploaded_pdf: werkzeug.datastructures.FileStorage containing the uploaded PDF.
        """
        self._session_check(order_sudo.company_id, order_sudo.partner_id.commercial_partner_id)
        bank_account_sudo = request.env['res.partner.bank'].browse(int(bank_account_id)).sudo()
        if not (request.env.user.partner_id.commercial_partner_id == bank_account_sudo.partner_id == order_sudo.partner_id):
            raise AccessError(_('Invalid bank account.'))

        if order_sudo.state not in ('purchase', 'done'):
            raise ValidationError(_('Bills can only be uploaded on confirmed orders.'))

        for invoice in order_sudo.invoice_ids.filtered(lambda invoice: invoice.state != 'cancel'):
            # The "Upload Bill" button should only show when this succeeds, so no need to handle exceptions.
            self._vendor_bill_cancel(invoice.id, order_sudo.id)

        # with_user() for correct create_uid, needed to know if we can cancel it ourselves from the portal.
        bill = order_sudo.with_user(request.env.user).with_context(mail_create_nolog=True).sudo()._create_invoices()
        bill.partner_bank_id = bank_account_sudo
        bill.with_context(no_new_invoice=True).message_post(
            body=_('Vendor bill uploaded by vendor on portal.'),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            attachments=[self._validate_and_read_vendor_attachment(uploaded_pdf)],
        )

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, access_token=None, bill_pdf=None, bank_account=None, expiration_ts=None, signature=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo._portal_verify_upload_bill_session(request.env.user.partner_id, expiration_ts, signature):
            # _verify_session ensures the logged in partner is a child of the partner on the PO
            request.session['purchase-vendor-verified-partner-id'] = request.env.user.partner_id.commercial_partner_id.id
            request.session['purchase-vendor-verified-until'] = int(time.time()) + VERIFIED_SESSION_DURATION_S

        if request.httprequest.method == 'POST' and bill_pdf and bank_account:
            try:
                self._process_uploaded_bill(order_sudo, bank_account, bill_pdf)
            except (AccessError, MissingError):
                return request.redirect('/my')

        report_type = kw.get('report_type')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type, report_ref='purchase.action_report_purchase_order', download=kw.get('download'))

        confirm_type = kw.get('confirm')
        if confirm_type == 'reminder':
            order_sudo.confirm_reminder_mail(kw.get('confirmed_date'))
        if confirm_type == 'reception':
            order_sudo._confirm_reception_mail()

        values = self._purchase_order_get_page_view_values(order_sudo, access_token, **kw)
        update_date = kw.get('update')
        if order_sudo.company_id:
            values['res_company'] = order_sudo.company_id
        if update_date == 'True':
            return request.render("purchase.portal_my_purchase_order_update_date", values)
        return request.render("purchase.portal_my_purchase_order", values)

    @http.route(['/my/purchase/<int:order_id>/update'], type='json', auth="public", website=True)
    def portal_my_purchase_order_update_dates(self, order_id=None, access_token=None, **kw):
        """User update scheduled date on purchase order line.
        """
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        updated_dates = []
        for id_str, date_str in kw.items():
            try:
                line_id = int(id_str)
            except ValueError:
                return request.redirect(order_sudo.get_portal_url())
            line = order_sudo.order_line.filtered(lambda l: l.id == line_id)
            if not line:
                return request.redirect(order_sudo.get_portal_url())

            try:
                updated_date = line._convert_to_middle_of_day(datetime.strptime(date_str, '%Y-%m-%d'))
            except ValueError:
                continue

            updated_dates.append((line, updated_date))

        if updated_dates:
            order_sudo._update_date_planned_for_lines(updated_dates)
        return Response(status=204)

    @http.route('/my/purchase/<int:order_id>/verify', type='http', methods=['POST'], auth='user', website=True)
    def portal_verify_email(self, order_id, **kw):
        """Sends out a verification email with a link that will create a session that will pass _session_check(). The
        email will always be sent to the partner on the PO. That person can choose to upload the bill themselves or
        forward it to someone else in their company (child of commercial partner).

        :param order_id: the purchase order for which the link should be sent.
        """
        try:
            po_sudo = self._document_check_access('purchase.order', order_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        odoobot = request.env.ref("base.partner_root")
        template = request.env.ref('purchase.email_template_edi_purchase_done')
        email_values = {
            'author_id': odoobot.id,
            'email_from': po_sudo.company_id.email_formatted,
        }
        template.sudo().send_mail(po_sudo.id, force_send=True, email_values=email_values)
        return request.redirect_query(f'/my/purchase/{po_sudo.id}', query=kw)

    def _vendor_bill_cancel(self, move_id, purchase_order_id):
        """Cancels move_id, provided that it's the user's own, non-validated vendor bill.

        :param move_id: the vendor bill to cancel.
        :param purchase_order_id: the purchase order it belongs to.
        :raise AccessError: if the user doesn't have permission to cancel move_id.
        :raise MissingError: if move_id does not exist."""
        po_sudo = self._document_check_access('purchase.order', purchase_order_id)
        self._session_check(po_sudo.company_id, po_sudo.partner_id.commercial_partner_id)

        move_sudo = request.env['account.move'].browse(move_id).sudo()
        partner_id = request.env.user.partner_id
        if move_sudo not in po_sudo.invoice_ids or not move_sudo._can_be_cancelled_by_vendor_partner(partner_id):
            raise AccessError(_('Bill can not be cancelled.'))

        move_sudo.button_cancel()

    @http.route('/my/bill/<int:move_id>/cancel', type='http', methods=['POST'], auth='user', website=True)
    def portal_vendor_bill_cancel(self, move_id, purchase_order_id, **kw):
        """Allows a portal user to cancel their own, non-validated vendor bills.

        :param move_id: the vendor bill to cancel.
        :param purchase_order_id: the purchase order to redirect back to.
        """
        try:
            self._vendor_bill_cancel(move_id, int(purchase_order_id))
        except (AccessError, MissingError):
            return request.redirect('/my')

        # stay on current page
        return request.redirect_query(f'/my/purchase/{purchase_order_id}', query=kw)

    def _check_vendor_creation_limit(self, model):
        """Check that created records by this user are under an acceptable limit.

        :params model: the model _name to check.
        :raise ValidationError: if the logged-in user created more than MAX_CREATED_BANK_RECORDS records."""
        record_count = request.env[model].with_context(active_test=False).sudo()\
            .search_count([('create_uid', '=', request.env.user.id)])
        if record_count >= MAX_CREATED_BANK_RECORDS:
            raise ValidationError(_('Please contact us to create additional bank accounts.'))

    def _sanity_check_bank_account(self, **kw):
        """Protect against common errors users may make, and ensure the values they provide make sense. These should
        be in sync with the values specified in the portal_bank_accounts template and the PurchaseBankAccount frontend
        widget.

        :params kw: a dict containing all required fields (should be checked already)."""
        self._check_vendor_creation_limit('res.partner.bank')
        bic = kw['bic']
        if not all(char for char in kw['bic'] if char.isalnum()) or len(bic) > 11:
            raise ValidationError(_('Please specify a valid SWIFT/BIC, up to 11 alphanumeric characters are allowed.'))

        # A well-behaved user won't see the errors below, their browser should stop them.
        if len(kw['name']) > 70:
            raise ValidationError(_('The name of your bank is too long, make sure you\'re not including the address.'))

        if len(kw['city']) > 50 or len(kw['street']) > 50 or len(kw.get('street2', '')) > 50:
            raise ValidationError(_('Please specify a valid city, street and suite, building or floor.'))

        if len(kw['zip']) > 10:
            raise ValidationError(_('Please specify a valid zip.'))

    def _process_added_bank_account(self, **kw):
        """Allows a portal user to create a new res.partner.bank and optionally a new res.bank. Before a res.bank is
        created, we check if already have a res.bank exactly like it. If not, we create a new one.

        :params kw: a values dict of both res.bank and res.partner.bank fields."""
        m2o_fields = {'state', 'country'}

        def form_value_to_domain(field, value):
            if field in m2o_fields:  # m2o
                return '=', int(value)
            if not value:  # falsy Char fields
                return 'in', ('', False)
            return '=', value

        optional_bank_fields = ['street2', 'state']
        required_bank_fields = ['bic', 'name', 'street', 'city', 'zip', 'country']
        bank_fields = optional_bank_fields + required_bank_fields
        if any(field not in kw for field in required_bank_fields):
            raise ValidationError(_('Missing required bank fields.'))

        ResPartnerBankSudo = request.env['res.partner.bank'].sudo()
        country_code = request.env['res.country'].browse(int(kw['country'])).code
        required_fields = ResPartnerBankSudo._get_required_frontend_bank_account_fields(country_code)
        if any(field not in kw for field in required_fields):
            raise ValidationError(_('Missing required bank account fields.'))

        regular_bank_fields = ResPartnerBankSudo._get_regular_frontend_bank_account_fields(country_code)
        for field in optional_bank_fields + required_bank_fields + regular_bank_fields:
            if field not in m2o_fields and kw.get(field):
                kw[field] = kw[field].strip()

        self._sanity_check_bank_account(**kw)

        # If res.bank is identical, reuse
        ResBankSudo = request.env['res.bank'].sudo()
        domain = [
            (field, *form_value_to_domain(field, kw[field]))
            for field in bank_fields
            if field in kw
        ]
        bank = ResBankSudo.search(domain, limit=1)

        if not bank:
            self._check_vendor_creation_limit('res.bank')
            bank = ResBankSudo.create({field: kw[field] for field in bank_fields if field in kw})

        values = {
            field: kw[field]
            for field in regular_bank_fields
            if field in kw
        }
        partner = request.env.user.partner_id.commercial_partner_id
        values['partner_id'] = partner.id
        values['bank_id'] = bank.id
        if partner.bank_ids:
            values['sequence'] = min(partner.bank_ids.mapped("sequence")) - 1  # make this the preferred bank account
        partner_bank = ResPartnerBankSudo.create(values)

        for attachment_field in ResPartnerBankSudo._get_attachment_frontend_bank_account_fields(country_code):
            if attachment_file := kw.get(attachment_field):
                filename, data = self._validate_and_read_vendor_attachment(attachment_file)
                request.env['ir.attachment'].sudo().create({
                    'res_model': 'res.partner.bank',
                    'res_id': partner_bank.id,
                    'name': filename,
                    'raw': data,
                })

    @http.route('/my/bank_account', type='http', methods=['GET', 'POST'], auth='user', website=True)
    def portal_my_bank_accounts(self, purchase_order_id=None, **kw):
        """Retrieve bank accounts belonging to the company of the logged-in user. Also provides the data needed to
        create a new bank account.

        :param purchase_order_id: optional purchase order to return to after POSTing.
        """
        partner = request.env.user.partner_id.commercial_partner_id
        try:
            self._session_check(request.env.company, partner)
        except AccessError:
            return request.redirect('/my')

        if request.httprequest.method == 'POST':
            self._process_added_bank_account(**kw)
            if purchase_order_id:
                try:
                    self._document_check_access('purchase.order', int(purchase_order_id))
                except (AccessError, MissingError):
                    return request.redirect('/my')
                return request.redirect_query(f'/my/purchase/{purchase_order_id}')

        return request.render('purchase.portal_bank_accounts', {
            'page_name': 'bank_accounts',
            'countries': request.env['res.country'].search([]),
            'states': request.env['res.country.state'].search([]),
            'bank_accounts': request.env['res.partner.bank'].sudo().search([('partner_id', '=', partner.id)]),
            'bank_account_fields': request.env['res.partner.bank']._get_frontend_bank_account_fields(),
        })

    @http.route('/my/bank_account/<int:bank_account_id>/archive', type='http', methods=['POST'], auth='user', website=True)
    def portal_archive_bank_account(self, bank_account_id, **kw):
        """Allows archiving of a bank account belonging to the company of the logged-in partner.

        :param bank_account_id: the bank account to archive.
        """
        partner = request.env.user.partner_id.commercial_partner_id
        try:
            self._session_check(request.env.company, partner)
        except AccessError:
            return request.redirect('/my')

        bank_sudo = request.env['res.partner.bank'].browse(bank_account_id).sudo()
        if bank_sudo.partner_id.commercial_partner_id != partner:
            return request.redirect('/my')

        bank_sudo.action_archive()
        return request.redirect_query('/my/bank_account', query=kw)

    @http.route('/my/bank_account/get_banks', type='http', methods=['GET'], auth='user', website=True, sitemap=False)
    def portal_get_banks(self, bic, **kw):
        """Retrieves res.bank data to automatically populate the bank creation form.

        :param bic: a prefix of a bic/swift code.
        """
        self._session_check(request.env.company, request.env.user.partner_id.commercial_partner_id)

        headers = [("Content-Type", "application/json")]
        if len(bic) < 4:
            return request.make_response(json.dumps([]), headers=headers)

        data = request.env["res.bank"].sudo().search(
            [("bic", "=ilike", f"{escape_psql(bic)}%")], limit=10
        ).mapped(lambda bank: {
            "id": bank.id,
            "bic": bank.bic,
            "name": bank.name,
            "street": bank.street,
            "street2": bank.street2,
            "city": bank.city,
            "state": bank.state.id,
            "zip": bank.zip,
            "country": bank.country.id,
        })

        return request.make_response(json.dumps(data), headers=headers)
