# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo.http import Controller, request, route

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class CustomController(Controller):
    _process_url = "/payment/custom/process"

    @route(_process_url, type="http", auth="public", methods=["POST"], csrf=False)
    def custom_process_transaction(self, reference=None):
        payment_data = {"reference": reference}
        _logger.info("Handling custom processing with data:\n%s", pprint.pformat(payment_data))
        if (
            tx_sudo := self
            .env["payment.transaction"]
            .sudo()
            ._search_by_reference("custom", payment_data)
        ):
            tx_sudo._record(payment_data)
        return request.redirect("/payment/status")
