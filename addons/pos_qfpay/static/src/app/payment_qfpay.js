import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

import { QFPay, QFPayError } from "./qfpay";

const { DateTime } = luxon;

export class PaymentQFpay extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.orm = this.env.services.orm;
        this.dialog = this.env.services.dialog;
        this.paymentLineResolvers = {};
        this.qfpay = new QFPay(this.env, this.payment_method_id, this._showError.bind(this));
    }

    async sendPaymentRequest(uuid) {
        await super.sendPaymentRequest(...arguments);
        const order = this.pos.getOrder();
        const line = order.getSelectedPaymentline();

        if (line.amount < 0) {
            const originalPayment = order.refunded_order_id.payment_ids.find(
                (l) => l.payment_method_id.id === this.payment_method_id.id
            );
            if (!originalPayment) {
                this._showError(
                    new QFPayError(
                        _t("No payment with %s found for this order.", this.payment_method_id.name)
                    )
                );
                return false;
            }
            if (this._isCreditCardPayment && originalPayment.amount !== -line.amount) {
                this._showError(
                    new QFPayError(_t("Credit card payments refund must be for the full amount."))
                );
                return false;
            }
            if (originalPayment.amount < -line.amount) {
                this._showError(
                    new QFPayError(
                        _t("Refund amount cannot be greater than the original payment amount.")
                    )
                );
                return false;
            }
            const currentDateTime = DateTime.now().setZone("Asia/Hong_Kong");
            const originalPaymentDate = DateTime.fromISO(originalPayment.create_date).setZone(
                "Asia/Hong_Kong"
            );
            if (
                !currentDateTime.hasSame(originalPaymentDate, "day") ||
                currentDateTime.hour >= 23
            ) {
                this._showError(
                    new QFPayError(
                        _t(
                            "Refunds can only be made on the same day before 23:00 HKT. Use the QFPay portal to perform this refund"
                        )
                    )
                );
                return false;
            }
            this.callQFPay(uuid, "cancel", {
                func_type: 1002,
                orderId: originalPayment.transaction_id,
                refund_amount: (-line.amount).toFixed(2),
            });
        } else {
            this.callQFPay(uuid, "trade", {
                func_type: 1001,
                amt: line.amount,
                channel: this.payment_method_id.qfpay_payment_type,
                out_trade_no: `${uuid}--${order.session_id.id}--${this.payment_method_id.id}`,
            });
        }

        line.setPaymentStatus("waitingCard");
        return this.waitForPaymentConfirmation(uuid);
    }

    waitForPaymentConfirmation(uuid) {
        return new Promise((resolve) => {
            this.paymentLineResolvers[uuid] = resolve;
        });
    }

    async sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        this.callQFPay(uuid, "cancel_request", {
            func_type: 5001,
        });
        return Promise.resolve(true);
    }

    async callQFPay(uuid, endpoint, payload) {
        const response = await this.qfpay.makeQFPayRequest(endpoint, payload);
        if (!response) {
            const resolver = this.paymentLineResolvers[uuid];
            resolver && resolver(false);
        }
        return response;
    }

    async handleQFPayStatusResponse(data) {
        const response = data.response;
        const line = this.pendingQFpayline;
        let lineMismatch = false;
        if (response.notify_type === "cancel") {
            lineMismatch =
                !line ||
                !line.pos_order_id.refunded_order_id.payment_ids.find(
                    (l) => l.uuid === data.line_uuid
                );
        } else {
            lineMismatch = !line || line.uuid !== data.line_uuid;
        }
        if (lineMismatch) {
            console.warn(
                "QFPay response received for a line that is not pending or does not match the current line."
            );
            return;
        }
        const isPaymentSuccessful = response.status === "1";
        if (isPaymentSuccessful) {
            line.payment_ref_no = response.chnlsn;
            line.transaction_id = response.syssn;
        } else {
            this._showError(
                new QFPayError(
                    _t("QFPay payment failed. Please try again or use a different payment method.")
                )
            );
        }
        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh )
        // we use the handlePaymentResponse method on the payment line
        const resolver = this.paymentLineResolvers?.[line.uuid];
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else {
            line.handlePaymentResponse(isPaymentSuccessful);
        }
    }

    get pendingQFpayline() {
        return this.pos.getPendingPaymentLine("qfpay");
    }

    get _isCreditCardPayment() {
        return ["card_payment", "unionpay_card", "amex_card"].includes(
            this.payment_method_id.qfpay_payment_type
        );
    }

    _showError(error) {
        this.dialog.add(AlertDialog, {
            title: _t("QFPay Error"),
            body: error.message,
        });
    }
}

register_payment_method("qfpay", PaymentQFpay);
