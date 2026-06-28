import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

import { PAYWAY_QR_CODE_METHOD } from "./const";

// When open payment screen
//  IF payment is aba
//      IF payment allow print on bill  
//          IF order has already print on bill with QR
//              Check payment transaction status
//              IF payment is complete
//                  Validate order -> complete order
//  Set a bus notification
//  If User stay in payment screen:
//      If receive webhook (from scan bill):     
//          complete order when
//  If User open QR popup:
//      If receive webhook (from scan qr popup dialog):
//          close open dialog
//          complete order

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        const busService = this.env.services.bus_service;

        this.channelName = null;
        this._paywayWebhookHandler = this._onPaywayWebhookNotification.bind(this);

        onMounted(async () => {
            const order = this.pos.get_order();

            const payment = order?.payment_ids.at(-1);
            const qrCodeMethod = payment?.payment_method_id?.qr_code_method;

            if (PAYWAY_QR_CODE_METHOD.includes(qrCodeMethod)) {
                this.channelName = "pos.order.payment.payway." + payment.transaction_id;
                busService.addChannel(this.channelName);
                busService.subscribe("notification", this._paywayWebhookHandler);
                this._completeOrderPayway(false);
            }
        });

        onWillUnmount(() => {
            if (this.channelName) {
                busService.deleteChannel(this.channelName);
                busService.unsubscribe("notification", this._paywayWebhookHandler);
            }
        });
    },

    async sendPaymentRequest(line) {
        // Setup bus notification handler before show QR Popup
        if (
            line.payment_method_id.payment_method_type === "qr_code" &&
            PAYWAY_QR_CODE_METHOD.includes(line.payment_method_id.qr_code_method)
        ) {
            if (!this.channelName) {
                const busService = this.env.services.bus_service;

                this.channelName = "pos.order.payment.payway." + line.transaction_id;
                busService.addChannel(this.channelName);
                busService.subscribe("notification", this._paywayWebhookHandler);
            }
        }
        return super.sendPaymentRequest(line);
    },

    async _completeOrderPayway(isValidateFromQRPopup) {
        /**
         * Attempt complete Order on condition:
         *  - Receive webhook callback on QR popup
         *  - Receive webhook callback on QR in printed bill
         *  - Check transaction API on QR in printed bill
         */
        const order = this.pos.get_order();
        if (!order) {
            return;
        }

        if (!isValidateFromQRPopup) {
            if (!order.payway_bill_nb_print || order.payway_bill_nb_print <= 0) {
                return;
            }
        }

        const payment = order.payment_ids.at(-1);
        if (!payment) {
            return;
        }

        if (!isValidateFromQRPopup) {
            if (
                !payment.payment_method_id ||
                !PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id.qr_code_method) ||
                !payment.payment_method_id.allow_qr_on_bill
            ) {
                return;
            }

        } else {
            if (
                !payment.payment_method_id ||
                !PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id.qr_code_method)
            ) {
                return;
            }
        }

        let is_payment_complete = false;
        try {
            is_payment_complete = await this.orm.call("pos.payment.method", "payway_verify_transaction", [
                [payment.payment_method_id.id],
                payment.transaction_id,
            ]);

        } catch (error) {
            return;
        }

        if (!is_payment_complete) {
            return;
        }

        this.dialog.closeAll();
        payment.handle_payment_response(true);
        this.validateOrder(false);
    },

    _onPaywayWebhookNotification(notification) {
        if (notification?.channel_name == this.channelName) {
            this._completeOrderPayway(true);
        }
    },
});