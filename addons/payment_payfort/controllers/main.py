# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
import pprint
import re
import werkzeug

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayfortController(http.Controller):
    _return_url = "/payment/payfort/return/"

    @http.route(["/payment/payfort/return"], type="http", auth="public", csrf=False)
    def payfort_return(self, **post):
        _logger.info(
            "Beginning Payfort form_feedback with post data %s", pprint.pformat(post)
        )  # debug
        request.env["payment.transaction"].sudo().form_feedback(post, "payfort")
        return werkzeug.utils.redirect("/payment/process")

    @http.route(
        ["/payment/payfort/notify"],
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def payfort_notification(self, **post):
        """
        Handle notifications coming from Payfort servers.

        Notification can be direct (immediately upon payment) or indirect (status change
        for an existing payment that was i.e. pending and got through asynchronously).

        The data we receive is in the same format as the redirect page (json) and
        can be processed like a normal feedback.
        """
        _logger.info(
            "Beginning Payfort notification feedback with post data %s",
            pprint.pformat(post),
        )
        # if the notification is for an s2s tx, the worker processing it might not
        # be finished - in this case the transaction won't be visible from this
        # db cursor yet. Check for transaction presence and return a nice error
        # to payfort - they will retry 10 times every 10 sec
        try:
            request.env["payment.transaction"].sudo()._payfort_form_get_tx_from_data(
                post
            )
        except ValidationError:
            raise werkzeug.exceptions.NotFound()
        request.env["payment.transaction"].sudo().form_feedback(post, "payfort")
        return "OK"

    @http.route(
        "/payment/payfort/merchant_page_values",
        auth="public",
        type="json",
        methods=["POST"],
    )
    def payfort_merchant_page_values(self, acquirer_id, partner_id):
        """Return the information needed to do a POST to a Payfort Merchant Page."""
        acquirer = request.env["payment.acquirer"].sudo().browse(int(acquirer_id))
        # TODO?: security check on partner? not sure
        partner = request.env["res.partner"].sudo().browse(int(partner_id))
        if not partner.exists():
            raise werkzeug.exceptions.BadRequest(
                "Cannot generate a tokenization form without a partner"
            )
        if not acquirer.exists() or not acquirer.provider == "payfort":
            raise werkzeug.exceptions.BadRequest(
                "The provided acquirer does not use Payfort"
            )
        res = {
            "values": acquirer._payfort_generate_s2s_values(partner_id=partner.id),
            "url": acquirer.payfort_get_form_action_url(),  # seems weird, but it's the same url as for forms
        }
        _logger.info(
            "Beginning Payfort tokenization process, merchant page POST values:\n%s",
            pprint.pformat(res),
        )
        return res

    @http.route(
        "/payment/payfort/merchant_page_return",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def payfort_merchant_page_return(self, **post):
        """Handle returns from the Payfort Merchant Page process (tokenization).

        This route is reached upon first returning from the tokenization process, in which case we
        create the token and validate it using a validation transaction (this step is *required*
        by Payfort, otherwise the token won't be saved).
        The rendered page will contain javascript code that will try to communicate to its parent
        frame to forward the result of the transaction to the initial payment page through JS custom
        events.

        If this route is called with a failed status, the token will not be saved and an error will
        be shown to the customer.
        """
        _logger.debug(
            "received merchant page tokenization return values %s", pprint.pformat(post)
        )
        if post.get("service_command") != "TOKENIZATION":
            raise werkzeug.exceptions.BadRequest(
                "POST data should contain a `service_command` param TOKENIZATION"
            )
        Token = request.env["payment.token"]
        merch_id, access_code, merch_ref = (
            post.get("merchant_identifier"),
            post.get("access_code"),
            post.get("merchant_reference"),
        )
        reference_pattern = r"^ODOO\-PARTNER\-[a-zA-Z]{10}\-(\d+)$"
        partner_ids = re.findall(reference_pattern, merch_ref)
        if not partner_ids:
            raise werkzeug.exceptions.BadRequest("Badly structured merchant_reference")
        post["partner_id"] = int(
            partner_ids[0]
        )  # must be included in the dict for s2s_process
        acquirer = (
            request.env["payment.acquirer"]
            .sudo()
            .search(
                [
                    ("payfort_merchant_identifier", "=", merch_id),
                    ("payfort_access_code", "=", access_code),
                ],
                limit=1,
            )
        )
        token = acquirer.s2s_process(post)
        # you might think the token is ready at this point, but you'd be wrong
        # this token can only be used to create a validation transaction using
        # a specific API, otherwise it's useless
        # we need to validate it
        if token:
            tx = token.with_context(payfort_validation=True).validate()
        else:
            # something went wrong, we received a failure response from the tokenization process
            # empty set, will display an error in frontend iframe and finish payment process
            tx = Token
        # to avoid a refresh & resubmit of POST-data, redirect to a landing page & hash
        # the info that is needed client-side to avoid abuse since the landing controller is public
        params = {
            "token_id": token.id or 0,
            "tx_id": tx.id or 0,
        }
        return self.sign_and_redirect(params)

    @http.route(
        "/payment/payfort/secure_merchant_page_return",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def payfort_secure_merchant_page_return(self, **post):
        """Handle returns from the Payfort Merchant Page process (tokenization) with 3D-Secure.

        This route will only be called if the previous tokenization step (the authorization
        transaction) triggered a 3D-Secure check; the result of this 3DS authentication
        will land here. Process the validation tx and mark the token as validated, as well
        as void the validation tx since it could not be voided automatically by the validation
        process (because of 3DS).

        The rendered page will contain javascript code that will try to communicate with the iframe
        that was initally opened for the payment process. Note that it is the same page as the
        previous authorization route, since the behaviour is mostly the same for the client code.

        If the authorization fails during this stage, the token that was generated will get archived
        immediately since it will not work.
        """
        Token = request.env["payment.token"]
        if post.get("command") != "AUTHORIZATION":
            raise werkzeug.exceptions.BadRequest(
                "POST data should contain a `command` param AUTHORIZATION"
            )
        success = (
            request.env["payment.transaction"].sudo().form_feedback(post, "payfort")
        )  # boolean (and not tx as one might think)
        tx = (
            request.env["payment.transaction"]
            .sudo()
            ._payfort_form_get_tx_from_data(post)
        )
        if success:
            # tokenization is always done with AUTHORIZATION command
            # we need to void - not refund
            tx.s2s_void_transaction()
            token = tx.payment_token_id
        else:
            # the validation transaction failed the 3ds process
            # -> no need for refund
            # -> token can't be used, it was either archive or unlink. I chose archive.
            tx.payment_token_id.action_archive()
            # empty set, will display an error in the frontend popup 3ds return
            token = Token
        # to avoid a refresh & resubmit of POST-data, redirect to a landing page & hash
        # the info that is needed client-side to avoid abuse since the landing controller is public
        params = {
            "token_id": token.id or 0,
            "tx_id": tx.id or 0,
        }
        return self.sign_and_redirect(params)

    def sign_and_redirect(self, params):
        """Add a sha-sginature to the payload and redirect to the client-side processing page."""
        db_secret = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("database.secret")
            .encode()
        )
        signature = hmac.new(
            db_secret, json.dumps(params, sort_keys=True).encode(), hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        url_params = werkzeug.urls.url_encode(params)
        return werkzeug.utils.redirect(
            "/payment/payfort/merchant_return?%s" % url_params
        )

    @http.route(
        "/payment/payfort/merchant_return",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=True,
    )
    def payfort_merchant_return(self, token_id, tx_id, signature, **kargs):
        params_check = {
            "token_id": int(token_id),
            "tx_id": int(tx_id),
        }
        db_secret = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("database.secret")
            .encode()
        )
        signature_check = hmac.new(
            db_secret,
            json.dumps(params_check, sort_keys=True).encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature_check, signature):
            raise werkzeug.exceptions.BadRequest("signature mismatch")
        token = (
            int(token_id)
            and request.env["payment.token"].sudo().browse(int(token_id))
            or request.env["payment.token"]
        )
        tx = (
            int(tx_id)
            and request.env["payment.transaction"].sudo().browse(int(tx_id))
            or request.env["payment.transaction"]
        )
        return request.render(
            "payment_payfort.payfort_merchant_page_return",
            {"token": token, "validation_tx": tx},
        )
