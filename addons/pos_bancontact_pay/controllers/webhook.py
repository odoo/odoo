import io

from PIL import Image

from odoo import http
from odoo.http import request
from odoo.tools.misc import file_path

from odoo.addons.pos_bancontact_pay.controllers.signature import (
    BancontactSignatureValidation,
)
from odoo.addons.pos_bancontact_pay.errors.exceptions import (
    BancontactSignatureValidationError,
)


class BancontactPayController(http.Controller):

    @http.route('/bancontact_pay/sticker/<int:payment_method_id>', type='http', auth='user')
    def download_sticker(self, payment_method_id):
        payment_method = request.env['pos.payment.method'].browse(payment_method_id)

        lang = request.env.context.get('lang')
        frame_lang = lang.split('_')[0] if lang else 'fr'
        supported_frames = ['fr', 'nl']
        if frame_lang not in supported_frames:
            frame_lang = 'fr'

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
    def bancontact_pay_webhook(self, config_id=None, ppid=None, mode=None):
        bancontact_signature_validation = BancontactSignatureValidation(request.httprequest, mode == "test")
        try:
            bancontact_signature_validation.verify_signature(ppid)
        except BancontactSignatureValidationError as e:
            return http.Response(str(e), status=403)

        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            return http.Response("Invalid or missing config_id parameter", status=400)

        pos_config = self.env['pos.config'].sudo().browse(config_id)
        if not pos_config.exists():
            return http.Response("Invalid POS configuration ID", status=400)

        data = request.get_json_data()
        bancontact_id = data.get("paymentId")
        bancontact_status = data.get("status")
        if bancontact_status not in ["SUCCEEDED", "AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"]:
            return http.Response(status=204)

        self._notify_pos(pos_config, bancontact_id, bancontact_status)

        return http.Response(status=200)

    def _notify_pos(self, pos_config, bancontact_id, bancontact_status):
        pos_config._notify(
            "BANCONTACT_PAY_PAYMENTS_NOTIFICATION",
            {
                "bancontact_id": bancontact_id,
                "bancontact_status": bancontact_status,
            },
        )
