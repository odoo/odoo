import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { rpc } from "@web/core/network/rpc";
import { onWillUnmount } from "@odoo/owl";

const REQUEST_TIMEOUT = 10000;

patch(PaymentPage.prototype, {
    setup() {
        super.setup();
        this.pollingTimeout = null;
        this.qrisPaymentLine = null;
        onWillUnmount(() => this.stopQRISPolling());
    },

    get showQrCode() {
        if (this.selectedPaymentMethod?.qr_code_method === "id_qr") {
            return !!this.state.qrCode;
        }
        return super.showQrCode;
    },

    paymentQRISPolling() {
        this.pollingTimeout = setTimeout(async () => {
            try {
                const isPaid = await this.confirmQRISPayment();
                if (isPaid === false) {
                    this.paymentQRISPolling();
                }
            } catch (error) {
                this.selfOrder.handleErrorNotification(error);
                this.selfOrder.paymentError = true;
                this.stopQRISPolling();
            }
        }, REQUEST_TIMEOUT);
    },

    stopQRISPolling() {
        clearTimeout(this.pollingTimeout);
        this.pollingTimeout = null;
        this.qrisPaymentLine = null;
    },

    async confirmQRISPayment() {
        const pm_line = this.qrisPaymentLine;
        if (!pm_line) {
            this.stopQRISPolling();
            return;
        }
        let result;

        try {
            result = await this.selfOrder.data.call(
                "pos.payment.method",
                "l10n_id_verify_qris_status",
                [[pm_line.payment_method_id.id], pm_line.pos_order_id.uuid]
            );
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
            this.stopQRISPolling();
            return;
        }

        if (!result) {
            return false; // payment still not paid so keeps polling
        }

        // Payment confirmed
        this.stopQRISPolling();

        try {
            await rpc(`/kiosk/payment/${this.selfOrder.config.id}/kiosk`, {
                order: this.selfOrder.currentOrder.serializeForORM(),
                access_token: this.selfOrder.access_token,
                payment_method_id: this.state.paymentMethodId,
            });
            return true;
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
            this.stopQRISPolling();
            return;
        }
    },

    async generateQRIScodeImg(payment) {
        this.state.qrCode = await this.selfOrder.generateQRIScode(payment);
    },

    async startPayment() {
        this.stopQRISPolling();
        let order = this.selfOrder.currentOrder;
        const pm = this.selectedPaymentMethod;
        const device = this.selfOrder.config.self_ordering_mode;

        if (!pm || pm.qr_code_method != "id_qr" || device !== "kiosk") {
            return super.startPayment(...arguments);
        }
        order = await this.selfOrder.sendDraftOrderToServer();

        try {
            const result = order.addPaymentline(pm);
            if (!result.status) {
                throw new Error(`Adding payment line failed: ${result.data}`);
            }
            const newPaymentLine = result.data;
            this.qrisPaymentLine = newPaymentLine;
            try {
                await this.generateQRIScodeImg(newPaymentLine);
            } catch (err) {
                order.removePaymentline(newPaymentLine);
                this.qrisPaymentLine = null;
                throw err;
            }
            this.paymentQRISPolling(); // start polling after QR is generated
        } catch (err) {
            this.selfOrder.handleErrorNotification(err);
            this.selfOrder.paymentError = true;
        }
    },

    back() {
        this.stopQRISPolling();
        // If payment method is QRIS then remove created payment line that is used to generate the QR
        const qrisPayment = this.selfOrder.currentOrder.payment_ids?.find(
            (p) => p.payment_method_id.qr_code_method === "id_qr"
        );
        if (qrisPayment) {
            this.selfOrder.currentOrder.removePaymentline(qrisPayment);
        }
        return super.back(...arguments);
    },
})
