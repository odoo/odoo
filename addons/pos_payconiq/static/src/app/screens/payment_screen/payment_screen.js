import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.orm = this.env.services.orm;
        this.bus_service = this.env.services.bus_service;

        if (!this.pos._hasPayconiqBusHandler) {
            this.bus_service.subscribe("pos_sync_payconiq", this._onPayconiqSync.bind(this));
            this.pos._hasPayconiqBusHandler = true;
        }
    },

    _onPayconiqSync({ status, uuid }) {
        const getLine = () => this.pos.models["pos.payment"].find((line) => line.uuid === uuid);

        // Identified
        if (status === "IDENTIFIED") {
            const line = getLine();
            if (line && line.payment_status === "waitingScanExternalQR") {
                line.setPaymentStatus("waitingPaymentExternalQR");
            }
        }

        // Success
        else if (status === "SUCCEEDED") {
            const line = getLine();
            if (line) {
                if (line.payment_status === "done") {
                    this.notification.add(_t("Payment received: %s", line.display_name), {
                        type: "success",
                    });
                } else {
                    line.setPaymentStatus("done");
                    this.autoValidateOrder({
                        currentOrder: line.pos_order_id,
                        paymentMethod: line.payment_method_id,
                        line,
                    });
                }
            }
        }

        // Failed or Expired or Cancelled
        else if (["AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"].includes(status)) {
            const line = getLine();
            if (line && line.payment_status !== "retry") {
                this.finalizeExternalQRCancellation(line);
            }
            const expiredMessage = _t("Payment expired");
            const failedMessage = _t("Payment failed");
            const cancelledMessage = _t("Payment cancelled");
            const message =
                status === "EXPIRED"
                    ? expiredMessage
                    : status === "CANCELLED"
                    ? cancelledMessage
                    : failedMessage;
            this.notification.add(message, { type: "warning" });
        }
    },

    async processExternalQRPayment(line) {
        if (line.payment_method_id.use_payment_terminal !== "payconiq") {
            return await super.processExternalQRPayment(line);
        }
        await this.processExternalQRPaymentPayconiq(line);

        // The bus service will handle the payment success or failure
        // Or through confirm/cancel buttons related to the payment line
        return false;
    },

    async processExternalQRPaymentPayconiq(line) {
        try {
            const description = `Payment at ${this.pos.company.name}\nPOS ${this.pos.config.name}`;
            const result = await this.orm.call(
                "pos.payment.method",
                "create_payconiq_payment",
                [line.payment_method_id.id],
                {
                    paymentUuid: line.uuid,
                    amount: line.amount,
                    currency: this.pos.currency.name,
                    posId: this.pos.config.id,
                    shopName: this.pos.config.name,
                    paymentMethodId: line.payment_method_id.id,
                    description: description,
                    is_sticker: line.payment_method_id.isExternalStickerQR,
                }
            );

            if (!result) {
                this.notification.add(_t("Failed to create payment"), { type: "danger" });
                return false;
            }

            line.setPaymentStatus("waitingScanExternalQR");
            line.payconiq_id = result.payconiq_id;
            line.qr_code = result.qr_code;

            if (line.payment_method_id.isExternalDisplayQR) {
                this.sendQRToCustomerDisplay(line);
            } else if (line.payment_method_id.isExternalStickerQR) {
                this.pos.stickerPaymentsInProgress.add(line.payment_method_id.id);
            }
            return true;
        } catch (error) {
            const title = _t("Failed to create payment.");
            const message =
                error.data?.message || _t("An error occurred while creating the payment.");
            this.notification.add(message, { type: "danger", title, sticky: true });
            return false;
        }
    },

    async cancelExternalQR(line) {
        if (
            line.payment_method_id.use_payment_terminal != "payconiq" ||
            !line.payment_method_id.isExternalQR
        ) {
            return await super.cancelExternalQR(line);
        }

        // Payment already initiated
        if (line.payment_status === "waitingPaymentExternalQR") {
            const cancelPayment = await new Promise((resolve) => {
                this.dialog.add(
                    ConfirmationDialog,
                    {
                        title: _t("Are you sure?"),
                        body: _t(
                            "The customer has already scanned the QR code. Are you sure you want to cancel the payment?"
                        ),
                        confirm: resolve.bind(null, false),
                        confirmLabel: _t("No"),
                        cancel: () => {},
                        cancelLabel: _t("Yes"),
                    },
                    { onClose: resolve.bind(null, true) }
                );
            });
            return cancelPayment;
        }

        // Payment not yet initiated
        try {
            const cancelled = await this.orm.call(
                "pos.payment.method",
                "cancel_payconiq_payment",
                [line.payment_method_id.id],
                {
                    payconiq_id: line.payconiq_id,
                }
            );
            if (!cancelled) {
                this.notification.add(_t("Failed to cancel payment"), { type: "danger" });
            }
        } catch (error) {
            const title = _t("Failed to cancel payment.");
            const message =
                error.data?.message || _t("An error occurred while cancelling the payment.");
            this.notification.add(message, { type: "danger", title, sticky: true });
        }

        // Don't block the flow on cancel errors
        return true;
    },
});
