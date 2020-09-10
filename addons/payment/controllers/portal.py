# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import urllib.parse
from datetime import timedelta

import psycopg2
import werkzeug

from odoo import _, fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.float_utils import float_repr

import odoo.addons.payment.utils as payment_utils

_logger = logging.getLogger(__name__)


class WebsitePayment(http.Controller):

    """
    This controller is independent from other modules implementing payments and allows the user
    going through all standard payment flows.

    It exposes several routes:
    - `/website_payment/pay` allows for arbitrary payments through a payment link.
    - `/website_payment/transaction` is the `init_tx_route` for the standard payment flow.
      It creates a draft transaction, and return the processing values necessary for the completion
      of the transaction.
    - `/website_payment/confirm` is the `landing_route` for the standard payment flow.
      It displays the payment confirmation page to the user when the transaction is validated.
    - `/my/payment_method` allows the user to create and manage tokens.
    - `/website_payment/validate` is the `landing_route` for the standard payment method validation
      flow. It redirects the user to `/my/payment_method` to display the result and start the flow
      over.
    """

    @http.route('/website_payment/pay', type='http', auth='public', website=True, sitemap=False)
    def pay(
        self, reference=None, amount=None, currency_id=None, partner_id=None, order_id=None,
        company_id=None, acquirer_id=None, access_token=None, **_kwargs
    ):
        """ Display the payment form with optional filtering of payment options.

        The filtering takes place on the basis of provided parameters, if any. If a parameter is
        incorrect or malformed, it is skipped to avoid preventing the user from making the payment.

        In addition to the desired filtering, a second one ensures that none of the following
        rules is broken:
            - Public users are not allowed to save their payment method as a token.
            - Payments made by public users should either *not* be made on behalf of a specific
              partner or have an access token validating the partner, amount and currency.
        We let access rights and security rules do their job for logged in users.

        :param str reference: The custom prefix to compute the full reference
        :param str amount: The amount to pay
        :param str currency_id: The desired currency, as a `res.currency` id
        :param str partner_id: The partner making the payment, as a `res.partner` id
        :param str order_id: The related order, as a `sale.order` id
        :param str company_id: The related company, as a `res.company` id
        :param str acquirer_id: The desired acquirer, as a `payment.acquirer` id
        :param str access_token: The access token used to authenticate the partner
        :param dict _kwargs: Optional data. This parameter is not used here.
        :return: The rendered checkout form
        :rtype: str
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """

        def _pick_company(_preferred_company_id, _order, _user_sudo):
            """ Pick the company that is the most relevant given the transaction context.

            The order's company is preferred over the desired company, while the user's company
            is used as fallback if neither of the first options is suitable.

            :param int _preferred_company_id|None: The preferred company, as a `res.company` id
            :param recordset _order|None: The related order, as a `sale.order` recordset
            :param recordset _user_sudo: The current user with sudo privileges, as a `res.users`
                                         recordset
            :return: The id of the relevant company
            :rtype: int
            """
            _company_id = None
            if _order:  # If a related order exists, pick its company for accounting reasons
                _company_id = _order.company_id.id
            elif _preferred_company_id:  # Otherwise, pick the company specified in the parameters
                _company_id = _preferred_company_id
            else:  # No company provided, fallback on the user's company
                _company_id = _user_sudo.company_id.id
            return _company_id

        def _select_payment_tokens(_acquirers, _partner_id):
            """ Select and return the payment tokens of the partner for the provided acquirers.

            :param recordset _acquirers: The acquirers, as a `payment.acquirer` recordset
            :param int _partner_id: The partner making the payment, as a `res.partner` id
            :return: The payment tokens for the given partner and acquirers
            :rtype: recordset of `payment.token`
            """
            payment_tokens = request.env['payment.token'].search(
                [('acquirer_id', 'in', _acquirers.ids), ('partner_id', '=', _partner_id)]
            )
            return payment_tokens

        # Cast numeric parameters as int or float to skip them if their str value is malformed
        order_id, currency_id, acquirer_id, partner_id, company_id = self.cast_as_numeric(
            [order_id, currency_id, acquirer_id, partner_id, company_id], numeric_type='int'
        )
        amount, = self.cast_as_numeric([amount], numeric_type='float')

        # Raise an HTTP 404 if a partner is provided with an invalid access token
        if partner_id:
            db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            if not payment_utils.check_access_token(
                access_token, db_secret, partner_id, amount, currency_id
            ):
                raise werkzeug.exceptions.NotFound  # Don't leak info about existence of an id

        user_sudo = request.env.user.sudo()
        logged_in = not user_sudo._is_public()
        # If the user is logged in, overwrite the partner set in the params with that of the user.
        # This is something that we want, since security rules are based on the partner and created
        # tokens should not be assigned to the public user. This should have no impact on the
        # transaction itself besides making reconciliation possibly more difficult (e.g. The
        # transaction and invoice partners are different).
        if logged_in:
            partner_id = user_sudo.partner_id.id
        elif not partner_id:
            return request.redirect(
                # Escape special characters to avoid loosing original params when redirected
                f'/web/login?redirect={urllib.parse.quote(request.httprequest.full_path)}'
            )

        # Instantiate transaction values to their default if not set in parameters
        amount = amount or 0.
        currency_id = currency_id or user_sudo.company_id.currency_id.id

        # If a sale order is provided, its currency and amount overwrite any value set before. For
        # reconciliation, we need both these values to match exactly that of the sale order.
        order_sudo = None
        if order_id:
            order_sudo = request.env['sale.order'].sudo().browse(order_id)
            currency_id = order_sudo.currency_id.id
            amount = order_sudo.amount_total

        # Pick the company that is the most relevant given the tx context to filter the acquirers
        company_id = _pick_company(company_id, order_sudo, user_sudo)

        # Select all acquirers that match the constraints
        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            company_id, partner_id, preferred_acquirer_id=acquirer_id
        )  # In sudo mode to read on the partner fields if the user is not logged in

        # Make sure that the currency exists and is active
        currency = request.env['res.currency'].browse(currency_id).exists()
        if not currency or not currency.active:
            currency = user_sudo.company_id.currency_id

        # Compute the fees taken by acquirers supporting the feature
        country_id = user_sudo.partner_id.country_id.id
        fees_by_acquirer = {acq_sudo: acq_sudo._compute_fees(amount, currency.id, country_id)
                            for acq_sudo in acquirers_sudo.filtered('fees_active')}

        tx_context = {
            'acquirers': acquirers_sudo,
            'tokens': _select_payment_tokens(acquirers_sudo, partner_id) if logged_in else [],
            'fees_by_acquirer': fees_by_acquirer,
            'show_tokenize_input': logged_in,  # Prevent saving payment methods on different partner
            'reference': reference or 'tx',  # Use 'tx' to always have a ref if it was not provided
            'amount': amount,
            'currency': currency,
            'partner_id': partner_id,
            'order_id': order_id,
            'access_token': access_token,
            'init_tx_route': '/website_payment/transaction',
            'landing_route': '/website_payment/confirm',
        }
        return request.render('payment.pay', tx_context)

    @http.route('/website_payment/transaction', type='json', auth='public', csrf=True)
    def transaction(
        self, payment_option_id, reference, amount, currency_id, partner_id, flow,
        tokenization_requested, is_validation, landing_route, access_token=None, **kwargs
    ):
        """ Create the transaction in draft and return its processing values.

        :param int payment_option_id: The payment option handling the transaction, as a
                                      `payment.acquirer` id or a `payment.token` id
        :param str reference: The custom prefix to compute the full reference
        :param float|None amount: The amount to pay in the given currency. None if in a payment
                                  method validation operation
        :param int|None currency_id: The currency of the transaction, as a `res.currency` id. None
                                     if in a payment method validation operation
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param str flow: The online payment flow of the transaction: 'redirect', 'direct' or 'token'
        :param bool tokenization_requested: Whether the user requested that a token is created
        :param bool is_validation: Whether the operation of the transaction is a validation
        :param str landing_route: The route the user is redirected to after the transaction
        :param str access_token: The access token used to authenticate the partner
        :param dict kwargs: Optional data. Locally processed keys: order_id
        :return: The values necessary for the processing of the transaction
        :rtype: dict
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """
        # Raise an HTTP 404 if the access token is provided but incorrect for the associated partner
        # or if it is not provided and the partner of the user is different that that of the param
        if access_token or request.env.user.partner_id.id != partner_id:
            db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            if not payment_utils.check_access_token(
                access_token, db_secret, partner_id, amount, currency_id
            ):
                raise werkzeug.exceptions.NotFound

        # Get the amount and currency from the acquirer if the transaction is a validation
        if is_validation:
            acquirer_sudo = request.env['payment.acquirer'].sudo().browse(payment_option_id)
            amount = acquirer_sudo._get_validation_amount()
            currency_id = acquirer_sudo._get_validation_currency().id

        # Prepare the create values that are common to all online payment flows
        order_id = kwargs.get('order_id')
        tx_reference = request.env['payment.transaction']._compute_reference(
            prefix=reference, sale_order_ids=([order_id] if order_id else [])
        )
        create_tx_values = {
            'reference': tx_reference,
            'amount': amount,
            'currency_id': currency_id,
            'partner_id': partner_id,
            'operation': f'online_{flow}' if not is_validation else 'validation',
        }

        processing_values = {}  # The generic and acquirer-specific values to process the tx
        if flow in ['redirect', 'direct']:  # Payment through (inline or redirect) form
            acquirer_sudo = request.env['payment.acquirer'].sudo().browse(payment_option_id)
            tokenize = bool(
                # Public users are not allowed to save tokens as their partner is unknown
                not request.env.user.sudo()._is_public()
                # Token is only saved if requested by the user and allowed by the acquirer
                and tokenization_requested and acquirer_sudo.allow_tokenization
            )
            tx_sudo = request.env['payment.transaction'].sudo().with_context(lang=None).create({
                'acquirer_id': acquirer_sudo.id,
                'tokenize': tokenize,
                **create_tx_values,
            })
            processing_values = tx_sudo._get_processing_values()
        elif flow == 'token':  # Payment by token
            token_sudo = request.env['payment.token'].sudo().browse(payment_option_id).exists()
            if not token_sudo:
                raise UserError(_("No token token with id %s could be found.", payment_option_id))
            if order_id:
                create_tx_values.update(sale_order_ids=[(6, 0, [int(order_id)])])
            tx_sudo = request.env['payment.transaction'].sudo().with_context(lang=None).create({
                'acquirer_id': token_sudo.acquirer_id.id,
                'token_id': payment_option_id,
                **create_tx_values,
            })  # Created in sudo to allowed writing on callback fields
            tx_sudo._send_payment_request()  # Tokens process transactions immediately
            # The dict of processing values is not filled in token flow since the user is redirected
            # to the payment process page directly from the client
        else:
            raise UserError(
                _("The payment should either be direct, with redirection, or made by a token.")
            )

        # Build the landing route with a new access token
        rounded_amount = float_repr(
            tx_sudo.amount, precision_digits=tx_sudo.currency_id.decimal_places
        )
        db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        access_token = payment_utils.generate_access_token(
            db_secret, tx_sudo.id, tx_sudo.reference, rounded_amount
        )
        tx_sudo.landing_route = f'{landing_route}?tx_id={tx_sudo.id}&access_token={access_token}'

        # Monitor the transaction to make it available in the portal
        PaymentPostProcessing.monitor_transactions(tx_sudo)

        return processing_values

    @http.route('/website_payment/confirm', type='http', auth='public', website=True, sitemap=False)
    def confirm(self, tx_id, access_token, **_kwargs):
        """ Display the payment confirmation page with the appropriate status message to the user.

        :param str tx_id: The transaction to confirm, as a `payment.transaction` id
        :param str access_token: The access token used to verify the user
        :param dict _kwargs: Optional data. This parameter is not used here.
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """
        tx_id, = self.cast_as_numeric([tx_id], numeric_type='int')
        if tx_id:
            tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)

            # Raise an HTTP 404 if the access token is invalid
            db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            rounded_amount = float_repr(
                tx_sudo.amount, precision_digits=tx_sudo.currency_id.decimal_places
            )
            if not payment_utils.check_access_token(
                access_token, db_secret, tx_sudo.id, tx_sudo.reference, rounded_amount
            ):
                raise werkzeug.exceptions.NotFound  # Don't leak info about existence of an id

            # Fetch the appropriate status message configured on the acquirer
            if tx_sudo.state == 'pending':
                status = 'warning'
                message = tx_sudo.acquirer_id.pending_msg
            elif tx_sudo.state in ('authorized', 'done'):
                status = 'success'
                message = tx_sudo.acquirer_id.done_msg
            else:
                status = 'danger'
                message = tx_sudo.state_message \
                          or _('An error occurred during the processing of this payment.')

            # Display the payment confirmation page to the user
            PaymentPostProcessing.remove_transactions(tx_sudo)
            render_values = {
                'tx': tx_sudo,
                'status': status,
                'message': message
            }
            return request.render('payment.confirm', render_values)
        else:
            # Display the portal homepage to the user
            return request.redirect('/my/home')

    @http.route('/my/payment_method', type='http', auth='user', website=True)
    def payment_method(self, **_kwargs):
        """ Display the form to manage payment methods.

        :param dict _kwargs: Optional data. This parameter is not used here.
        :return: The rendered manage form
        :rtype: str
        """
        partner = request.env.user.partner_id
        acquirers = request.env['payment.acquirer']._get_compatible_acquirers(
            request.env.company.id, partner.id, allow_tokenization=True
        )
        tokens = set(partner.payment_token_ids).union(
            partner.commercial_partner_id.sudo().payment_token_ids
        )  # Show all partner's tokens, regardless of which acquirer is available
        tx_context = {
            'acquirers': acquirers,
            'tokens': tokens,
            'reference': 'validation',
            'partner_id': partner.id,
            'init_tx_route': '/website_payment/transaction',
            'landing_route': '/website_payment/validate',
        }
        return request.render('payment.payment_methods', tx_context)

    @http.route('/website_payment/validate', type='http', auth='user', website=True, sitemap=False)
    def validate(self, tx_id, **_kwargs):
        """ Refund a payment method validation transaction and redirect the user.

        :param str tx_id: The token registration transaction to confirm, as a
                          `payment.transaction` id
        :param dict _kwargs: Optional data. This parameter is not used here.
        """
        tx_id, = self.cast_as_numeric([tx_id], numeric_type='int')
        if tx_id:
            tx = request.env['payment.transaction'].browse(tx_id)
            tx._send_refund_request()
            PaymentPostProcessing.remove_transactions(tx)

        # Send the user back to the "Manage Payment Methods" page
        return request.redirect('/my/payment_method')

    @staticmethod
    def cast_as_numeric(str_values, numeric_type='int'):
        """ Cast a list of string as numeric values. Incompatible values are replaced by None.

        :param list[str] str_values: The list of values to cast as the specified numeric type
        :param str numeric_type: The name ('int' or 'float') of the numeric type to cast to.
        :return: The casted values, some being possibly replaced by None if incompatible
        :rtype: tuple[numeric|None]
        """
        assert numeric_type in ('int', 'float')

        numeric_values = []
        for str_value in str_values:
            numeric_value = None
            try:
                if str_value is not None:
                    numeric_value = int(str_value) if numeric_type == 'int' else float(str_value)
            except (ValueError, OverflowError):
                pass
            numeric_values.append(numeric_value)
        return tuple(numeric_values)


class PaymentPostProcessing(http.Controller):

    """
    This controller is responsible for the monitoring and finalization of the post-processing of
    transactions.

    It exposes the route `/payment/status`: All payment flows must go through this route at some
    point to allow the user checking on the transactions' status, and to trigger the finalization of
    their post-processing.
    """

    MONITORED_TX_IDS_KEY = '__payment_monitored_tx_ids__'

    @http.route('/payment/status', type='http', auth='public', website=True, sitemap=False)
    def status(self, **_kwargs):
        """ Display the payment status page.

        :param dict _kwargs: Optional data. This parameter is not used here.
        :return: The rendered status page
        :rtype: str
        """
        return request.render('payment.payment_status')

    @http.route('/payment/status/poll', type='json', auth='public', csrf=True)
    def poll_status(self):
        """ Fetch the transactions to display on the status page and finalize their post-processing.

        :return: The post-processing values of the transactions
        :rtype: dict
        """
        # Retrieve recent user's transactions from the session
        limit_date = fields.Datetime.now() - timedelta(days=1)
        monitored_txs = request.env['payment.transaction'].sudo().search([
            ('id', 'in', self.get_monitored_transaction_ids()),
            ('last_state_change', '>=', limit_date)
        ])
        if not monitored_txs:  # The transaction was not correctly created
            return {
                'success': False,
                'error': 'no_tx_found',
            }

        # Build the dict of display values with the display message and post-processing values
        display_values_list = []
        for tx in monitored_txs:
            display_message = None
            if tx.state == 'pending':
                display_message = tx.acquirer_id.pending_msg
            elif tx.state == 'done':
                display_message = tx.acquirer_id.done_msg
            elif tx.state == 'cancel':
                display_message = tx.acquirer_id.cancel_msg
            display_values_list.append({
                'display_message': display_message,
                **tx._get_post_processing_values(),
            })

        # Stop monitoring already processed transactions
        processed_txs = monitored_txs.filtered('is_post_processed')
        self.remove_transactions(processed_txs)

        # Finalize post-processing of transactions before displaying them to the user
        txs_to_post_process = (monitored_txs - processed_txs).filtered(lambda t: t.state == 'done')
        success, error = True, None
        try:
            txs_to_post_process._finalize_post_processing()
        except psycopg2.OperationalError:  # A collision of accounting sequences occurred
            # Rollback and try later
            request.env.cr.rollback()
            success = False
            error = 'tx_process_retry'
        except Exception as e:
            request.env.cr.rollback()
            success = False
            error = str(e)
            _logger.exception(
                f"encountered an error while post-processing transactions with ids "
                f"{', '.join([str(tx_id) for tx_id in txs_to_post_process.ids])}. "
                f"exception: \"{e}\""
            )

        return {
            'success': success,
            'error': error,
            'display_values_list': display_values_list,
        }

    @staticmethod
    def monitor_transactions(transactions):
        """ Add the ids of the provided transactions to the list of monitored transaction ids.

        :param recordset transactions: The transactions to monitor, as a `payment.transaction`
                                       recordset
        :return: None
        """
        if transactions:
            monitored_tx_ids = request.session.get(PaymentPostProcessing.MONITORED_TX_IDS_KEY, [])
            request.session[PaymentPostProcessing.MONITORED_TX_IDS_KEY] = list(
                set(monitored_tx_ids).union(transactions.ids)
            )

    @staticmethod
    def get_monitored_transaction_ids():
        """ Return the ids of transactions being monitored.

        Only the ids and not the recordset itself is returned to allow the caller browsing the
        recordset with sudo privileges, and using the ids in a custom query.

        :return: The ids of transactions being monitored
        :rtype: list
        """
        return request.session.get(PaymentPostProcessing.MONITORED_TX_IDS_KEY, [])

    @staticmethod
    def remove_transactions(transactions):
        """ Remove the ids of the provided transactions from the list of monitored transaction ids.

        :param recordset transactions: The transactions to remove, as a `payment.transaction`
                                       recordset
        :return: None
        """
        if transactions:
            monitored_tx_ids = request.session.get(PaymentPostProcessing.MONITORED_TX_IDS_KEY, [])
            request.session[PaymentPostProcessing.MONITORED_TX_IDS_KEY] = [
                tx_id for tx_id in monitored_tx_ids if tx_id not in transactions.ids
            ]
