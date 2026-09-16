import pprint

from werkzeug.exceptions import Forbidden

from odoo.http import Controller, request, route

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class CustomController(Controller):
    _process_url = "/payment/custom/process"

    @route(_process_url, type="http", auth="public", methods=["POST"], csrf=False)
    def custom_process_transaction(self, **post):
        _logger.info("Handling custom processing with data:\n%s", pprint.pformat(post))
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            ._search_by_reference("custom", post)
        )
        if tx_sudo:
            payment_utils.admit_notification(
                tx_sudo.provider_id, lambda: self._check_access_token(post, tx_sudo)
            )
            tx_sudo._process("custom", post)
        return request.redirect("/payment/status")

    @staticmethod
    def _check_access_token(data, tx_sudo):
        if not payment_utils.is_access_token_valid(
            data.get("access_token"), tx_sudo.reference, tx_sudo.amount
        ):
            _logger.warning(
                "Refused custom processing of %s: invalid access token.",
                tx_sudo.reference,
            )
            raise Forbidden
