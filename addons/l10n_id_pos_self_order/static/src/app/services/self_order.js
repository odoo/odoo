import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { ConnectionLostError } from "@web/core/network/rpc";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(SelfOrder.prototype, {
    async generateQRIScode(payment) {
        let qr;
        try {
            qr = await this.data.call(
                "pos.payment.method",
                "get_qr_code_url",
                [
                    [payment.payment_method_id.id],
                    payment.amount,
                    payment.pos_order_id.name + " " + payment.pos_order_id.tracking_number,
                    "",
                    this.currency.id,
                    payment.pos_order_id.partner_id?.id,
                ],
                {
                    context: {
                        qris_model: "pos.order",
                        qris_model_id: payment.pos_order_id.uuid,
                    },
                }
            );
        } catch (error) {
            qr = payment.payment_method_id.default_qr;
            if (!qr) {
                let message;
                if (error instanceof ConnectionLostError) {
                    message = _t(
                        "Connection to the server has been lost. Please check your internet connection."
                    );
                } else {
                    message = error.data?.message || error.message;
                }
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Failure to generate Payment QR Code"),
                    body: message,
                });
                throw error;
            }
        }
        return qr;
    },
});
