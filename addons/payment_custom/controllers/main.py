import pprint

from odoo.http import Controller, request, route

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class CustomController(Controller):
    _process_url = "/payment/custom/process"

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @route(
        _process_url,
        type="http",
        auth="receiver",
        receiver="payment.transaction:_receiver_for_custom_process",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def custom_process_transaction(self, **post):
        _logger.info("Handling custom processing with data:\n%s", pprint.pformat(post))
        request.admission.subject._process("custom", request.admission.extra["post"])
        return request.redirect("/payment/status")
