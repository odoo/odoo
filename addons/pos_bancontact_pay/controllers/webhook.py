import io
import logging
import uuid

from PIL import Image

from odoo import http
from odoo.http import request
from odoo.tools.misc import file_path

from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.controllers.signature import (
    BancontactSignatureValidation,
)
from odoo.addons.pos_bancontact_pay.errors.exceptions import (
    BancontactSignatureValidationError,
)

_logger = logging.getLogger(__name__)


class BancontactPayController(http.Controller):

    @http.route('/bancontact_pay/sticker/<int:payment_method_id>', type='http', auth='user')
    def download_sticker(self, payment_method_id):
        payment_method = request.env['pos.payment.method'].browse(payment_method_id)

        lang = request.env.context.get('lang')
        frame_lang = lang.split('_')[0] if lang else 'en'
        supported_frames = ['en', 'fr', 'nl', 'de']
        if frame_lang not in supported_frames:
            frame_lang = 'en'

        # load frame
        frame_path = file_path(f'pos_bancontact_pay/static/img/frames/frame_{frame_lang}.png')
        frame = Image.open(frame_path).convert("RGBA")

        # fetch qr code
        qr_bytes = payment_method._fetch_bancontact_sticker_image()
        qr = Image.open(io.BytesIO(qr_bytes)).convert("RGBA")

        # resize QR
        qr_size = int(frame.width * 0.6)
        qr = qr.resize((qr_size, qr_size))

        # center QR
        x = (frame.width - qr.width) // 2
        y = (frame.height - qr.height) // 2
        frame.paste(qr, (x, y), qr)

        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        content = buffer.getvalue()

        filename = f"{payment_method.name}.png"
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
            ('Cache-Control', 'no-cache'),
        ]

        return request.make_response(content, headers)

    @http.route(["/bancontact_pay/webhook"], type="http", auth="public", methods=["POST"], csrf=False)
    def bancontact_pay_webhook(self, config_id=None, payment_method_id=None):
        log_prefix = f"{const.LOG_PREFIX} - {uuid.uuid4().hex[:8]}"
        _logger.info("%s webhook received: config_id=%s, payment_method_id=%s", log_prefix, config_id, payment_method_id)
        payment_method = self._get_bancontact_payment_method(payment_method_id)
        if not payment_method:
            _logger.error("%s webhook rejected: invalid payment_method_id=%s", log_prefix, payment_method_id)
            return http.Response("Invalid POS configuration", status=400)

        bancontact_signature_validation = BancontactSignatureValidation(request.httprequest, payment_method.bancontact_test_mode)
        try:
            bancontact_signature_validation.verify_signature(payment_method.bancontact_ppid)
        except BancontactSignatureValidationError as e:
            _logger.warning("%s webhook rejected: %s", log_prefix, e)
            return http.Response("Invalid signature", status=403)

        pos_config = self._get_pos_config(config_id)
        if not pos_config or payment_method not in pos_config.payment_method_ids:
            _logger.error("%s webhook rejected: payment_method_id=%s not configured on config_id=%s", log_prefix, payment_method_id, config_id)
            return http.Response("Invalid POS configuration", status=400)

        data = request.get_json_data()
        bancontact_id = data.get("paymentId")
        bancontact_status = data.get("status")
        if bancontact_status not in ["SUCCEEDED", "AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"]:
            _logger.warning("%s webhook ignored: unsupported status=%s (paymentId=%s)", log_prefix, bancontact_status, bancontact_id)
            return http.Response(status=204)

        payment = self._get_bancontact_payment(bancontact_id, payment_method, pos_config)
        if payment and self._is_bancontact_payment_finalized(payment):
            _logger.info("%s webhook ignored: payment already finalized (paymentId=%s)", log_prefix, bancontact_id)
            return http.Response(status=204)

        _logger.info("%s webhook processed: paymentId=%s, status=%s", log_prefix, bancontact_id, bancontact_status)
        self._notify_pos(pos_config, bancontact_id, bancontact_status)

        return http.Response(status=200)

    def _get_bancontact_payment_method(self, payment_method_id):
        try:
            payment_method_id = int(payment_method_id)
        except (TypeError, ValueError):
            return None
        payment_method = self.env["pos.payment.method"].sudo().browse(payment_method_id)
        if not payment_method.exists() or payment_method.payment_provider != "bancontact_pay":
            return None
        return payment_method

    def _get_bancontact_payment(self, bancontact_id, payment_method, pos_config):
        if not bancontact_id:
            return None
        return self.env["pos.payment"].sudo().search([
            ("bancontact_id", "=", bancontact_id),
            ("payment_method_id", "=", payment_method.id),
            ("pos_order_id.config_id", "=", pos_config.id),
        ], limit=1)

    def _is_bancontact_payment_finalized(self, payment):
        return payment.payment_status == "done" or payment.pos_order_id.state != "draft"

    def _get_pos_config(self, config_id):
        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            return None
        pos_config = self.env['pos.config'].sudo().browse(config_id)
        return pos_config if pos_config.exists() else None

    def _notify_pos(self, pos_config, bancontact_id, bancontact_status):
        pos_config._notify(
            "BANCONTACT_PAY_PAYMENTS_NOTIFICATION",
            {
                "bancontact_id": bancontact_id,
                "bancontact_status": bancontact_status,
            },
        )
