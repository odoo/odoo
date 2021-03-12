# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import pprint
from werkzeug import urls
from requests.exceptions import HTTPError

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.addons.payment_stripe_sca.controllers.main import StripeControllerSCA as StripeController
from odoo.addons.payment_stripe.models.payment import INT_CURRENCIES
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class PaymentAcquirerStripeSCA(models.Model):
    _inherit = "payment.acquirer"

    def stripe_form_generate_values(self, tx_values):
        self.ensure_one()

        base_url = self.get_base_url()
        stripe_session_data = {
            "payment_method_types[]": "card",
            "line_items[][amount]": int(
                tx_values["amount"]
                if tx_values["currency"].name in INT_CURRENCIES
                else float_round(tx_values["amount"] * 100, 2)
            ),
            "line_items[][currency]": tx_values["currency"].name,
            "line_items[][quantity]": 1,
            "line_items[][name]": tx_values["reference"],
            "client_reference_id": tx_values["reference"],
            "success_url": urls.url_join(base_url, StripeController._success_url)
            + "?reference=%s" % tx_values["reference"],
            "cancel_url": urls.url_join(base_url, StripeController._cancel_url)
            + "?reference=%s" % tx_values["reference"],
            "payment_intent_data[description]": tx_values["reference"],
            "customer_email": tx_values.get("partner_email") or tx_values.get("billing_partner_email"),
        }
        tx_values["session_id"] = self._create_stripe_session(stripe_session_data)

        return tx_values

    def _stripe_request(self, url, data=False, method="POST"):
        self.ensure_one()
        stripe_url = 'https://%s/' % (self._get_stripe_api_url())
        url = urls.url_join(stripe_url, url)
        headers = {
            "AUTHORIZATION": "Bearer %s" % self.sudo().stripe_secret_key,
            "Stripe-Version": "2019-05-16",  # SetupIntent need a specific version
        }
        resp = requests.request(method, url, data=data, headers=headers)
        # Stripe can send 4XX errors for payment failure (not badly-formed requests)
        # check if error `code` is present in 4XX response and raise only if not
        # cfr https://stripe.com/docs/error-codes
        # these can be made customer-facing, as they usually indicate a problem with the payment
        # (e.g. insufficient funds, expired card, etc.)
        # if the context key `stripe_manual_payment` is set then these errors will be raised as ValidationError,
        # otherwise, they will be silenced, and the will be returned no matter the status.
        # This key should typically be set for payments in the present and unset for automated payments
        # (e.g. through crons)
        if not resp.ok and self._context.get('stripe_manual_payment') and (400 <= resp.status_code < 500 and resp.json().get('error', {}).get('code')):
            try:
                resp.raise_for_status()
            except HTTPError:
                _logger.error(resp.text)
                stripe_error = resp.json().get('error', {}).get('message', '')
                error_msg = " " + (_("Stripe gave us the following info about the problem: '%s'") % stripe_error)
                raise ValidationError(error_msg)
        return resp.json()

    def _create_stripe_session(self, kwargs):
        self.ensure_one()
        resp = self._stripe_request("checkout/sessions", kwargs)
        if resp.get("payment_intent") and kwargs.get("client_reference_id"):
            tx = (
                self.env["payment.transaction"]
                .sudo()
                .search([("reference", "=", kwargs["client_reference_id"])])
            )
            tx.stripe_payment_intent = resp["payment_intent"]
        return resp["id"]

    def _create_setup_intent(self, kwargs):
        self.ensure_one()
        params = {"usage": "off_session"}
        _logger.info(
            "_stripe_create_setup_intent: Sending values to stripe, values:\n%s",
            pprint.pformat(params),
        )

        res = self._stripe_request("setup_intents", params)

        _logger.info(
            "_stripe_create_setup_intent: Values received:\n%s", pprint.pformat(res)
        )
        return res

    @api.model
    def stripe_s2s_form_process(self, data):
        last4 = data.get("card", {}).get("last4")
        if not last4:
            # PM was created with a setup intent, need to get last4 digits through
            # yet another call -_-
            acquirer_id = self.env["payment.acquirer"].browse(int(data["acquirer_id"]))
            pm = data.get("payment_method")
            res = acquirer_id._stripe_request(
                "payment_methods/%s" % pm, data=False, method="GET"
            )
            last4 = res.get("card", {}).get("last4", "****")

        payment_token = (
            self.env["payment.token"]
            .sudo()
            .create(
                {
                    "acquirer_id": int(data["acquirer_id"]),
                    "partner_id": int(data["partner_id"]),
                    "stripe_payment_method": data.get("payment_method"),
                    "name": "XXXXXXXXXXXX%s" % last4,
                    "acquirer_ref": data.get("customer"),
                }
            )
        )
        return payment_token

    def stripe_s2s_form_validate(self, data):
        return True


class PaymentTransactionStripeSCA(models.Model):
    _inherit = "payment.transaction"

    stripe_payment_intent = fields.Char(
        string="Stripe Payment Intent ID", readonly=True
    )
    stripe_payment_intent_secret = fields.Char(string='Stripe Payment Intent Secret', readonly=True)

    def _get_json_fields(self):
        res = super()._get_json_fields()
        res.append('stripe_payment_intent_secret')
        return res

    def _get_processing_info(self):
        res = super()._get_processing_info()
        if self.acquirer_id.provider == 'stripe':
            stripe_info = {
                'stripe_payment_intent': self.stripe_payment_intent,
                'stripe_payment_intent_secret': self.stripe_payment_intent_secret,
                'stripe_publishable_key': self.acquirer_id.stripe_publishable_key,
            }
            res.update(stripe_info)
        return res

    def _create_stripe_charge(self, acquirer_ref=None, tokenid=None, email=None):
        raise NotImplementedError(
            "This method can no longer be used with the payment_stripe_sca module."
        )

    def form_feedback(self, data, acquirer_name):
        if data.get("reference") and acquirer_name == "stripe":
            transaction = self.env["payment.transaction"].search(
                [("reference", "=", data["reference"])]
            )

            url = "payment_intents/%s" % transaction.stripe_payment_intent
            resp = transaction.acquirer_id._stripe_request(url)
            if resp.get("charges") and resp.get("charges").get("total_count"):
                resp = resp.get("charges").get("data")[0]

            data.update(resp)
            _logger.info(
                "Stripe: entering form_feedback with post data %s"
                % pprint.pformat(data)
            )
        # note: luckily, the base stripe module did not override this method, avoiding
        # me from using a context key to avoid this call in the parent model
        return super(PaymentTransactionStripeSCA, self).form_feedback(data, acquirer_name)

    def _stripe_create_payment_intent(self, acquirer_ref=None, email=None):
        if self.stripe_payment_intent:
            _logger.info(
                "_stripe_create_payment_intent: trying to create an intent when one already exists (tx #%s), refetching values for intent %s",
                self.id, self.stripe_payment_intent
            )
            res =  self.acquirer_id._stripe_request("payment_intents/%s" % self.stripe_payment_intent, method="GET")
            _logger.info(
                "_stripe_create_payment_intent: Values received:\n%s", pprint.pformat(res)
                )
            return res
        if not self.payment_token_id.stripe_payment_method:
            # old token before installing stripe_sca, need to fetch data from the api
            self.payment_token_id._stripe_sca_migrate_customer()
        charge_params = {
            "amount": int(
                self.amount
                if self.currency_id.name in INT_CURRENCIES
                else float_round(self.amount * 100, 2)
            ),
            "currency": self.currency_id.name.lower(),
            "confirm": True,
            "off_session": True,
            "payment_method": self.payment_token_id.stripe_payment_method,
            "customer": self.payment_token_id.acquirer_ref,
            "description": self.reference,
        }
        if not self.env.context.get('off_session'):
            charge_params.update(setup_future_usage='off_session', off_session=False)
        _logger.info(
            "_stripe_create_payment_intent: Sending values to stripe, values:\n%s",
            pprint.pformat(charge_params),
        )

        res = self.acquirer_id._stripe_request("payment_intents", charge_params)
        if res.get("charges") and res.get("charges").get("total_count"):
            res = res.get("charges").get("data")[0]

        _logger.info(
            "_stripe_create_payment_intent: Values received:\n%s", pprint.pformat(res)
        )
        return res

    def stripe_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        result = self._stripe_create_payment_intent(
            acquirer_ref=self.payment_token_id.acquirer_ref, email=self.partner_email
        )
        return self._stripe_s2s_validate_tree(result)

    def _create_stripe_refund(self):
        refund_params = {
            "charge": self.acquirer_reference,
            "amount": int(
                float_round(self.amount * 100, 2)
            ),  # by default, stripe refund the full amount (we don't really need to specify the value)
            "metadata[reference]": self.reference,
        }

        _logger.info(
            "_create_stripe_refund: Sending values to stripe URL, values:\n%s",
            pprint.pformat(refund_params),
        )
        res = self.acquirer_id._stripe_request("refunds", refund_params)
        _logger.info("_create_stripe_refund: Values received:\n%s", pprint.pformat(res))
        return res

    @api.model
    def _stripe_form_get_tx_from_data(self, data):
        """ Given a data dict coming from stripe, verify it and find the related
        transaction record. """
        reference = data.get("reference")
        if not reference:
            stripe_error = data.get("error", {}).get("message", "")
            _logger.error(
                "Stripe: invalid reply received from stripe API, looks like "
                "the transaction failed. (error: %s)",
                stripe_error or "n/a",
            )
            error_msg = _("We're sorry to report that the transaction has failed.")
            if stripe_error:
                error_msg += " " + (
                    _("Stripe gave us the following info about the problem: '%s'")
                    % stripe_error
                )
            error_msg += " " + _(
                "Perhaps the problem can be solved by double-checking your "
                "credit card details, or contacting your bank?"
            )
            raise ValidationError(error_msg)

        tx = self.search([("reference", "=", reference)])
        if not tx:
            error_msg = _("Stripe: no order found for reference %s") % reference
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        elif len(tx) > 1:
            error_msg = _("Stripe: %s orders found for reference %s") % (
                len(tx),
                reference,
            )
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    def _stripe_s2s_validate_tree(self, tree):
        self.ensure_one()
        if self.state not in ("draft", "pending"):
            _logger.info(
                "Stripe: trying to validate an already validated tx (ref %s)",
                self.reference,
            )
            return True

        status = tree.get("status")
        tx_id = tree.get("id")
        tx_secret = tree.get("client_secret")
        vals = {"date": fields.datetime.now(), "acquirer_reference": tx_id, "stripe_payment_intent": tx_id, "stripe_payment_intent_secret": tx_secret}
        if status == "succeeded":
            self.write(vals)
            self._set_transaction_done()
            self.execute_callback()
            if self.type == "form_save":
                s2s_data = {
                    "customer": tree.get("customer"),
                    "payment_method": tree.get("payment_method"),
                    "card": tree.get("payment_method_details").get("card"),
                    "acquirer_id": self.acquirer_id.id,
                    "partner_id": self.partner_id.id,
                }
                token = self.acquirer_id.stripe_s2s_form_process(s2s_data)
                self.payment_token_id = token.id
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        if status in ("processing", "requires_action"):
            self.write(vals)
            self._set_transaction_pending()
            return True
        if status == 'requires_payment_method':
            self._set_transaction_cancel()
            self.acquirer_id._stripe_request('payment_intents/%s/cancel' % self.stripe_payment_intent)
            return False
        else:
            error = tree.get("failure_message") or tree.get('error', {}).get('message')
            self._set_transaction_error(error)
            return False

    def _stripe_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if data.get("amount") != int(
            self.amount
            if self.currency_id.name in INT_CURRENCIES
            else float_round(self.amount * 100, 2)
        ):
            invalid_parameters.append(("Amount", data.get("amount"), self.amount * 100))
        if data.get("currency").upper() != self.currency_id.name:
            invalid_parameters.append(
                ("Currency", data.get("currency"), self.currency_id.name)
            )
        if (
            data.get("payment_intent")
            and data.get("payment_intent") != self.stripe_payment_intent
        ):
            invalid_parameters.append(
                (
                    "Payment Intent",
                    data.get("payment_intent"),
                    self.stripe_payment_intent,
                )
            )
        return invalid_parameters


class PaymentTokenStripeSCA(models.Model):
    _inherit = "payment.token"

    stripe_payment_method = fields.Char("Payment Method ID")

    @api.model
    def stripe_create(self, values):
        if values.get("stripe_payment_method") and not values.get("acquirer_ref"):
            partner_id = self.env["res.partner"].browse(values.get("partner_id"))
            payment_acquirer = self.env["payment.acquirer"].browse(
                values.get("acquirer_id")
            )

            # create customer to stipe
            customer_data = {"email": partner_id.email}
            cust_resp = payment_acquirer._stripe_request("customers", customer_data)

            # link customer with payment method
            api_url_payment_method = (
                "payment_methods/%s/attach" % values["stripe_payment_method"]
            )
            method_data = {"customer": cust_resp.get("id")}
            payment_acquirer._stripe_request(api_url_payment_method, method_data)
            return {"acquirer_ref": cust_resp["id"]}
        return values

    def _stripe_create_customer(self, token, description=None, acquirer_id=None):
        raise NotImplementedError(
            "This method can no longer be used with the payment_stripe_sca module."
        )

    def _stripe_sca_migrate_customer(self):
        """Migrate a token from the old implementation of Stripe to the SCA one.

        In the old implementation, it was possible to create a valid charge just by
        giving the customer ref to ask Stripe to use the default source (= default
        card). Since we have a one-to-one matching between a saved card, this used to
        work well - but now we need to specify the payment method for each call and so
        we have to contact stripe to get the default source for the customer and save it
        in the payment token.
        This conversion will happen once per token, the first time it gets used following
        the installation of the module."""
        self.ensure_one()
        url = "customers/%s" % (self.acquirer_ref)
        data = self.acquirer_id._stripe_request(url, method="GET")
        sources = data.get('sources', {}).get('data', [])
        pm_ref = False
        if sources:
            if len(sources) > 1:
                _logger.warning('stripe sca customer conversion: there should be a single saved source per customer!')
            pm_ref = sources[0].get('id')
        else:
            url = 'payment_methods'
            params = {
                'type': 'card',
                'customer': self.acquirer_ref,
            }
            payment_methods = self.acquirer_id._stripe_request(url, params, method='GET')
            cards = payment_methods.get('data', [])
            if len(cards) > 1:
                _logger.warning('stripe sca customer conversion: there should be a single saved source per customer!')
            pm_ref = cards and cards[0].get('id')
        if not pm_ref:
            raise ValidationError(_('Unable to convert Stripe customer for SCA compatibility. Is there at least one card for this customer in the Stripe backend?'))
        self.stripe_payment_method = pm_ref
        _logger.info('converted old customer ref to sca-compatible record for payment token %s', self.id)
