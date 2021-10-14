# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict
from datetime import datetime

from odoo import fields, http
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request, Response
from odoo.tools import image_process, format_date
from odoo.tools.translate import _
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager

from odoo.osv.expression import OR


class CustomerPortal(portal.CustomerPortal):

    # fields for res.partner.bank
    MANDATORY_PARTNER_BANK_FIELDS = {
        "acc_number": "acc_number",
    }
    OPTIONAL_PARTNER_BANK_FIELDS = {
        "acc_holder_name": "acc_holder_name",
    }
    # fields for res.bank
    MANDATORY_BANK_FIELDS = {
        "name": "bank_name",
        "bic": "bic",
    }

    def _prepare_portal_counters_values(self, counters):
        values = super()._prepare_portal_counters_values(counters)
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

    def _prepare_portal_overview_values(self):
        values = super()._prepare_portal_overview_values()
        values['purchase_rfq_counters'] = [
            {
                'description': _("Requests for Quotation"),
                'counter': 'rfq_count',
            },
        ]
        values['purchase_counters'] = [
            {
                'description': _("Current Orders"),
                'counter': 'purchase_count',
            },
        ]
        return values

    def _get_main_address_bank_details_changes(self, bank_data, partner_bank_data):
        """Compare the form data and the record data to see if there was any change and mark them.
        Here are the conditions to trigger a "change":
            * there is no record, but at least one value in the form is not falsy
            * there is a record, the form value is different from the record value, and at least
              one of them is not falsy
        The main purpose of this function is to be able to preemptively catch a partner bank change
        to warn the user that the operation will be logged and the commercial_partner will be notified
        """
        partner = request.env.user.partner_id
        main_partner_bank = bank = None
        if partner.bank_ids:
            main_partner_bank = min(partner.bank_ids, key=lambda bank: bank.sequence)
            bank = main_partner_bank.bank_id

        bank_changes = []
        for key, value in bank_data.items():
            if (value and not bank) or (bank and value != getattr(bank, key) and
                (value or getattr(bank, key))):
                bank_changes.append(key)
        partner_bank_changes = []
        for key, value in partner_bank_data.items():
            if (value and not main_partner_bank) or (main_partner_bank and value != getattr(main_partner_bank, key) and
                (value or getattr(main_partner_bank, key))):
                partner_bank_changes.append(key)
        # if acc_holder_name is not set, it is equivalent to the partner name, and therefore the triggered "change" should be ignored
        # and the data value updated to False
        if partner_bank_data['acc_holder_name'] == partner.name and not main_partner_bank.acc_holder_name:
            partner_bank_changes.remove('acc_holder_name')
            partner_bank_data['acc_holder_name'] = False

        return bank_changes, partner_bank_changes

    @http.route(['/my/bank_account_warnings'], type='json', auth="user", website=True)
    def main_address_bank_details_form_warnings(self, data, **kw):
        """The feature allowing to edit a partner main bank account is touchy, so we want to inform the
        user that the changes will be logged and the commercial_partner will be notified.
        """
        partner_bank_fields = {**self.MANDATORY_PARTNER_BANK_FIELDS, **self.OPTIONAL_PARTNER_BANK_FIELDS}
        bank_fields = self.MANDATORY_BANK_FIELDS
        partner_bank_data = {key: data.get(value, False) for key, value in partner_bank_fields.items()}
        bank_data = {key: data.get(value, False) for key, value in bank_fields.items()}
        warning_messages = []
        partner = request.env.user.partner_id

        bank_changes, partner_bank_changes = self._get_main_address_bank_details_changes(bank_data, partner_bank_data)

        if bank_changes or partner_bank_changes:
            warning_messages.append(_("You are changing a bank account of %(company_name)s. By default, payments coming from %(portal_company_name)s will go to the new bank account.\nThis change will be notified via email to: %(commercial_partner_name)s.",
                company_name=partner.company_id.name, portal_company_name=request.env.company.name, commercial_partner_name=partner.commercial_partner_id.name))
        if "acc_number" in partner_bank_changes and partner_bank_data['acc_number']:
            warning_messages.append(_("By changing the bank account number, the previous bank account will be archived and a new one will be created."))
        if "bic" in bank_changes or 'name' in bank_changes:
            existing_bank_ids = request.env['res.bank'].search([('bic', '=', bank_data['bic'])])
            matching_bank_id = existing_bank_ids.filtered(lambda bank_id: bank_id.name == bank_data['name'])
            if existing_bank_ids and not matching_bank_id:
                warning_messages.append(_("An existing bank with the provided BIC/SWIFT was found, but the names do not match.\nThe existing bank will be used instead:\nBIC/SWIFT: %(bic)s\nName: %(name)s",
                bic=existing_bank_ids[0].bic, name=existing_bank_ids[0].name))
        return warning_messages

    def _send_main_address_bank_details_warning_message(self, partner):
        date_reference = format_date(request.env, fields.Date.context_today(partner), lang_code=partner.lang, date_format="short")
        portal_company_name = request.env.company.name
        # chatter
        odoobot = request.env.ref('base.partner_root')
        message = _("On %(date_reference)s, %(partner_name)s modified a bank account of %(company_name)s.\n\
            By default, payments coming from %(portal_company_name)s will go to the new bank account.",
            date_reference=date_reference, partner_name=partner.name, company_name=partner.company_id.name, portal_company_name=portal_company_name)
        partner.message_post(body=message,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
            author_id=odoobot.id)
        # email
        template = request.env.ref('purchase.mail_template_data_portal_bank_informations_changed')
        if not template:
            raise UserError(_('The template "Portal: Bank Informations Change" not found to warn the Commercial Entity of a Bank Information Change'))
        template.with_context(portal_company_name=portal_company_name, date_reference=date_reference).send_mail(partner.id, force_send=True)

    def main_address_bank_details_form_validate(self, bank_data, partner_bank_data):
        error = dict()
        error_message = []

        partner = request.env.user.partner_id  # if not partner -> error because no validation possible

        for field_name in self.MANDATORY_PARTNER_BANK_FIELDS:
            if not partner_bank_data.get(field_name):
                error[self.MANDATORY_PARTNER_BANK_FIELDS[field_name]] = 'missing'
        for field_name in self.MANDATORY_BANK_FIELDS:
            if not bank_data.get(field_name):
                error[self.MANDATORY_BANK_FIELDS[field_name]] = 'missing'

        partner_bank_changes = self._get_main_address_bank_details_changes(bank_data, partner_bank_data)[1]

        if 'acc_number' in partner_bank_changes and partner_bank_data['acc_number']:
            existing_partner_bank_id = request.env['res.partner.bank'].search(['&',
                ('sanitized_acc_number', '=', sanitize_account_number(partner_bank_data['acc_number'])),
                ('company_id', '=', partner.company_id.id)])
            # unicity constraint is on sanitized_acc_number + company_id
            if existing_partner_bank_id:
                error['acc_number'] = 'error'
                error_message.append(_('Account Number must be unique'))

        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))
        return error, error_message

    def _prepare_address_operation_values(self, read=True, partner_id=None, **post):
        values = super()._prepare_address_operation_values(read, partner_id, **post)

        partner = request.env.user.partner_id
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        contact = Partner.browse(partner_id) if partner_id else False
        is_main_address = contact and contact.id == partner.id
        if not is_main_address:
            return values

        Bank = request.env['res.bank'].sudo()
        PartnerBank = request.env['res.partner.bank'].sudo()
        if contact and contact.bank_ids:
            main_partner_bank = min(contact.bank_ids, key=lambda bank: bank.sequence)
            bank = main_partner_bank.bank_id
        else:
            main_partner_bank = False
            bank = False
        partner_bank_fields = {**self.MANDATORY_PARTNER_BANK_FIELDS, **self.OPTIONAL_PARTNER_BANK_FIELDS}
        partner_bank_data = {}
        bank_fields = self.MANDATORY_BANK_FIELDS
        bank_data = {}
        bank_error = {}
        bank_error_message = []

        if not read:
            partner_bank_data = {key: post.get(value, False) for key, value in partner_bank_fields.items()}
            bank_data = {key: post.get(value, False) for key, value in bank_fields.items()}

            bank_changes, partner_bank_changes = self._get_main_address_bank_details_changes(bank_data, partner_bank_data)
            if bank_changes or partner_bank_changes:
                bank_error, bank_error_message = self.main_address_bank_details_form_validate(bank_data, partner_bank_data)
                if not bank_error:
                    partner_bank_data['partner_id'] = contact.id
                    # To avoid duplicating a bank due to a misspelled name, search only from bic and replace bank_data['name'] if necessary
                    bank = Bank.search([('bic', '=', bank_data['bic'])], limit=1)
                    if not bank:
                        bank = Bank.create(bank_data)
                    partner_bank_data['bank_id'] = bank.id
                    if main_partner_bank and main_partner_bank.acc_number == partner_bank_data['acc_number']:
                        # if the account number did not change, we edit the record
                        main_partner_bank.sudo().write(partner_bank_data)
                    else:
                        # if the account number is new (or did change), we create a new record (and archive the old one)
                        if main_partner_bank:
                            main_partner_bank.sudo().action_archive()
                        partner_bank_data['sequence'] = 1
                        PartnerBank.create(partner_bank_data)
                    self._send_main_address_bank_details_warning_message(contact)
            partner_bank_view_data = {value: partner_bank_data.get(key, False) for key, value in partner_bank_fields.items()}
            bank_view_data = {value: bank_data.get(key, False) for key, value in bank_fields.items()}
        else:
            partner_bank_view_data = {value: getattr(main_partner_bank, key) for key, value in partner_bank_fields.items() if main_partner_bank}
            bank_view_data = {value: getattr(bank, key) for key, value in bank_fields.items() if bank}

        values['error'].update(bank_error)
        values.update({
            **bank_view_data,
            **partner_bank_view_data,
            'bank_error_message': bank_error_message,
        })
        return values

    def _render_portal(self, template, page, date_begin, date_end, sortby, filterby, domain, searchbar_filters, default_filter, url, history, page_name, key, searchbar_inputs, search_domain, search=None, search_in='all'):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if searchbar_filters:
            # default filter
            if not filterby:
                filterby = default_filter
            domain += searchbar_filters[filterby]['domain']

        if search_domain:
            domain += search_domain

        # count for pager
        count = PurchaseOrder.search_count(domain)

        # make pager
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search': search, 'search_in': search_in},
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
            'searchbar_inputs': searchbar_inputs,
            'search': search,
            'search_in': search_in,
            'filterby': filterby,
            'default_url': url,
            'company': request.env.company
        })
        return request.render(template, values)

    def _purchase_order_get_page_view_values(self, order, access_token, **kwargs):
        #
        def resize_to_48(b64source):
            if not b64source:
                b64source = base64.b64encode(request.env['ir.http']._placeholder())
            return image_process(b64source, size=(48, 48))

        values = {
            'order': order,
            'resize_to_48': resize_to_48,
            'report_type': 'html',
            'company': request.env.company
        }
        if order.state in ('sent'):
            history = 'my_rfqs_history'
        else:
            history = 'my_purchases_history'
        return self._get_page_view_values(order, access_token, values, history, False, **kwargs)

    @http.route(['/my/rfq', '/my/rfq/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests_for_quotation(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', **kw):
        if search_in and search:
            search_domain = self._rfq_get_search_domain(search_in, search)
        else:
            search_domain = None
        return self._render_portal(
            "purchase.portal_my_purchase_rfqs",
            page, date_begin, date_end, sortby, filterby,
            [('state', '=', 'sent')],
            {},
            None,
            "/my/rfq",
            'my_rfqs_history',
            'rfq',
            'rfqs',
            self._rfq_get_searchbar_inputs(),
            search_domain,
            search,
            search_in,
        )

    def _rfq_get_searchbar_inputs(self):
        values = {
            'all': {'input': 'all', 'label': _('Search in All'), 'order': 1},
            'name': {'input': 'name', 'label': _('Search in Name'), 'order': 2},
        }
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    def _rfq_get_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('name', 'all'):
            search_domain.append([('name', 'ilike', search)])
        return OR(search_domain)

    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', **kw):
        if search_in and search:
            search_domain = self._purchase_get_search_domain(search_in, search)
        else:
            search_domain = None
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
            'orders',
            self._purchase_get_searchbar_inputs(),
            search_domain,
            search,
            search_in,
        )

    def _purchase_get_searchbar_inputs(self):
        values = {
            'all': {'input': 'all', 'label': _('Search in All'), 'order': 1},
            'name': {'input': 'name', 'label': _('Search in Name'), 'order': 2},
        }
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    def _purchase_get_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('name', 'all'):
            search_domain.append([('name', 'ilike', search)])
        return OR(search_domain)

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
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

    @http.route(['/my/purchase/<int:order_id>/invoices/<int:invoice_id>'], type='http', auth='user', website=True)
    def portal_my_purchase_order_vendor_bill(self, order_id=None, invoice_id=None, access_token=None, **kwargs):
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._invoice_get_page_view_values(invoice_sudo, access_token, **kwargs)
        values.update({
            'page_name': 'invoice_from_purchase',
            'company': request.env.company,
            'order_id': order_sudo
        })
        return request.render("account.portal_invoice_page", values)

    @http.route(['/my/purchase/<int:order_id>/update'], type='http', methods=['POST'], auth="public", website=True)
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
