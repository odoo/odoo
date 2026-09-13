from odoo import _, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinPaymentQrCode(models.AbstractModel):
    _name = "mixin.payment.qr.code"
    _description = "Payment QR Code Rendering"

    def _can_render_payment_qr_code(self):
        self.check_singleton()
        return bool(
            self.partner_bank_id
            and self.partner_bank_id.allow_out_payment
            and self.payment_channel_id.code == "manual"
            and self.payment_type == "outbound"
            and self.currency_id
            and self.amount
        )

    @_debug.perf.timed
    def _render_payment_qr_code(self, amount, communication):
        self.check_singleton()
        if not self._can_render_payment_qr_code():
            return False
        qr_code = self.partner_bank_id.prepare_qr_code_base64(
            amount, communication, communication, self.currency_id, self.partner_id
        )
        if not qr_code:
            return False
        return f'''
            <img class="border border-dark rounded" src="{qr_code}"/>
            <br/>
            <strong class="text-center">{_("Scan me with your banking app.")}</strong>
        '''
