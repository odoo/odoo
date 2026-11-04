# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request

from odoo.addons.account.controllers import portal
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.portal import PaymentPortal


class PortalAccount(portal.PortalAccount, PaymentPortal):

    def _invoice_get_page_view_values(self, invoice, access_token, payment=False, amount=None, **kwargs):
        # EXTENDS account

        values = super()._invoice_get_page_view_values(invoice, access_token, amount=amount, **kwargs)

        if not invoice._has_to_be_paid():
            # Do not compute payment-related stuff if given invoice doesn't have to be paid.
            return {
                **values,
                'payment': payment,  # We want to show the dialog even when everything has been paid (with a custom message)
            }

        epd = values.get('epd_discount_amount_currency', 0.0)
        discounted_amount = invoice.amount_residual - epd

        common_view_values = self._get_common_page_view_values(
            invoices_data={
                'partner': invoice.partner_id,
                'company': invoice.company_id,
                'total_amount': invoice.amount_total,
                'currency': invoice.currency_id,
                'amount_residual': discounted_amount,
                'landing_route': invoice.get_portal_url(),
                'transaction_route': f'/invoice/transaction/{invoice.id}',
            },
            access_token=access_token,
            **kwargs)

        amount_custom = float(amount or 0.0)
        values |= {
            **common_view_values,
            'amount_custom': amount_custom,
            'payment': payment,
            'invoice_id': invoice.id,
            'invoice_name': invoice.name,
            'show_epd': epd,
        }
        return values

    @http.route(['/my/invoices/overdue'], type='http', auth='public', methods=['GET'], website=True, sitemap=False)
    def portal_my_overdue_invoices(self, access_token=None, **kw):
        try:
            request.env['account.move'].check_access('read')
        except (AccessError, MissingError):
            return request.redirect('/my')

        overdue_invoices = request.env['account.move'].search(self._get_overdue_invoices_domain())

        values = self._overdue_invoices_get_page_view_values(overdue_invoices, **kw)
        return request.render("account_payment.portal_overdue_invoices_page", values) if 'payment' in values else request.redirect('/my/invoices')

    def _overdue_invoices_get_page_view_values(self, overdue_invoices, **kwargs):
        values = {'page_name': 'overdue_invoices'}

        if len(overdue_invoices) == 0:
            return values

        first_invoice = overdue_invoices[0]
        partner = first_invoice.partner_id
        company = first_invoice.company_id
        currency = first_invoice.currency_id

        if any(invoice.partner_id != partner for invoice in overdue_invoices):
            raise ValidationError(_("Overdue invoices should share the same partner."))
        if any(invoice.company_id != company for invoice in overdue_invoices):
            raise ValidationError(_("Overdue invoices should share the same company."))
        if any(invoice.currency_id != currency for invoice in overdue_invoices):
            raise ValidationError(_("Overdue invoices should share the same currency."))

        total_amount = sum(overdue_invoices.mapped('amount_total'))
        amount_residual = sum(overdue_invoices.mapped('amount_residual'))
        batch_name = company.get_next_batch_payment_communication() if len(overdue_invoices) > 1 else first_invoice.name
        values.update({
            'payment': {
                'date': fields.Date.context_today(request.env.user),
                'reference': batch_name,
                'amount': total_amount,
                'currency': currency,
            },
            'amount': total_amount,
        })

        common_view_values = self._get_common_page_view_values(
            invoices_data={
                'partner': partner,
                'company': company,
                'total_amount': total_amount,
                'currency': currency,
                'amount_residual': amount_residual,
                'payment_reference': batch_name,
                'landing_route': '/my/invoices/',
                'transaction_route': '/invoice/transaction/overdue',
            },
            **kwargs)
        values |= common_view_values
        return values

    def _get_invoice_payment_options_context(self, invoice_partner, company, amount, currency):
        """Return the payment context from which the available payment options of invoices are
        computed.

        The invoice portal page and the invoice transaction route both use this context, so the
        transaction route accepts the same payment options that the page shows. Override this
        method to add a filter to the payment options of invoices.

        :param res.partner invoice_partner: The partner of the invoices.
        :param res.company company: The company of the invoices.
        :param float amount: The amount to pay.
        :param res.currency currency: The currency of the invoices.
        :return: The kwargs of `_get_available_payment_options`.
        :rtype: dict
        """
        logged_in = not self.env.user._is_public()
        partner_sudo = self.env.user.partner_id if logged_in else invoice_partner
        return self._get_payment_options_context(
            (company or self.env.company).id, partner_sudo.id, amount, currency.id
        )

    def _get_common_page_view_values(self, invoices_data, access_token=None, **kwargs):
        payment_options_context = self._get_invoice_payment_options_context(
            invoices_data['partner'],
            invoices_data['company'],
            invoices_data['total_amount'],
            invoices_data['currency'],
        )
        partner_id = payment_options_context['partner_id']
        company_id = payment_options_context['company_id']
        partner_sudo = self.env['res.partner'].sudo().browse(partner_id)
        invoice_company = self.env['res.company'].sudo().browse(company_id)

        # Prepare the portal page values
        company_mismatch = not PaymentPortal._can_partner_pay_in_company(
            partner_sudo, invoice_company
        )
        portal_page_values = {
            'company_mismatch': company_mismatch,
            'expected_company': invoice_company,
        }

        # Prepare the payment form values
        payment_form_values = self._prepare_payment_form_values(
            **(kwargs | payment_options_context)
        )

        # Prepare the payment context
        payment_context = {
            'currency': invoices_data['currency'],
            'partner_id': partner_sudo.id,
            'transaction_route': invoices_data['transaction_route'],
            'landing_route': invoices_data['landing_route'],
            'access_token': access_token,
            'payment_reference': invoices_data.get('payment_reference', False),
        }

        # Merge the dictionaries while allowing the redefinition of keys
        return (
            portal_page_values
            | payment_form_values
            | payment_context
            | self._get_extra_payment_form_values(**kwargs)
        )

    @http.route()
    def portal_my_invoice_detail(self, invoice_id, payment_token=None, amount=None, **kw):
        # EXTENDS account

        # If we have a custom payment amount, make sure it hasn't been tampered with
        if amount and not payment_utils.check_access_token(payment_token, invoice_id, amount):
            return request.redirect('/my')
        return super().portal_my_invoice_detail(invoice_id, amount=amount, **kw)
