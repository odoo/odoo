import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { uuidv4 } from "@point_of_sale/utils";

export class PaymentBancontact extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.supports_refunds = false;
    }

    async sendPaymentRequest(line) {
        if (line.isBancontactRefund) {
            return this.sendRefundRequest(line);
        }
        if (
            !line.bancontact_id ||
            !line.qr_code ||
            !["waiting", "waitingScan", "waitingCancel"].includes(line.payment_status)
        ) {
            const { bancontact_id, qr_code } = await this.callPaymentMethod(
                "create_bancontact_payment",
                [
                    line.payment_method_id.id,
                    {
                        uuid: line.uuid,
                        amount: line.amount,
                        currency: this.pos.currency.name,
                        configId: this.pos.config.id,
                        shopName: this.pos.config.name,
                        description: _t(
                            "Payment at %s\nPOS %s",
                            this.pos.company.name,
                            this.pos.config.name
                        ),
                    },
                ]
            );
            line.bancontact_id = bancontact_id;
            line.qr_code = qr_code;
        }

        if (line.payment_method_id.bancontact_usage === "display") {
            this.pos.displayQrCode(line);
        }
        return true;
    }

    async sendRefundRequest(line) {
        line.uiState.bancontactIdempotencyKey ||= uuidv4();
        const { bancontact_refund_id, bancontact_refund_status } = await this.callPaymentMethod(
            "create_bancontact_refund",
            [
                line.payment_method_id.id,
                {
                    refunded_payment_id: line.bancontact_refunded_payment_id.id,
                    amount: line.amount,
                    idempotency_key: line.uiState.bancontactIdempotencyKey,
                    description: _t(
                        "Refund at %s\nPOS %s",
                        this.pos.company.name,
                        this.pos.config.name
                    ),
                },
            ]
        );
        line.bancontact_refund_id = bancontact_refund_id;
        return bancontact_refund_status;
    }

    refundToPaymentStatus(refundStatus) {
        const paymentStatuses = {
            PENDING: "waiting",
            REFUNDED: "done",
            FAILED: undefined,
        };
        return paymentStatuses[refundStatus];
    }

    async checkRefundStatus(lines) {
        if (!lines.length) {
            return;
        }
        const statuses = await this.callPaymentMethod("get_bancontact_refund_status", [
            lines[0].payment_method_id.id,
            lines.map((line) => [
                line.bancontact_refunded_payment_id.bancontact_id,
                line.bancontact_refund_id,
            ]),
        ]);
        for (const line of lines) {
            line.setBancontactRefundStatus(statuses[line.bancontact_refund_id]);
        }
    }

    async sendPaymentCancel(line) {
        const blockingErrorCodes = [422];
        const askForceCancel = async (errorCode) => {
            let message = _t(
                "The cancellation could not be completed. Do you want to force the cancellation?"
            );
            if (errorCode === 422) {
                message = _t(
                    "The customer is currently completing the payment, so it cannot be cancelled at this time.\n" +
                        "If you need to cancel it, please ask the customer to do so on their device or force the cancellation."
                );
            }
            return new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Oh snap !"),
                    body: message,
                    confirmLabel: _t("Close"),
                    confirm: () => resolve(false),
                    cancelLabel: _t("Force Cancel"),
                    cancel: () => resolve(true),
                    dismiss: () => resolve(false),
                });
            });
        };

        try {
            await this.callPaymentMethod("cancel_bancontact_payment", [
                line.payment_method_id.id,
                line.bancontact_id,
            ]);
            line.bancontact_id = null;
            line.qr_code = null;
            return true;
        } catch (error) {
            const message = error.data?.message || "";
            const errorCode = blockingErrorCodes.find((code) => message.includes(`ERR: ${code}`));
            const forceCancel = errorCode ? await askForceCancel(errorCode) : true;

            if (forceCancel) {
                line.forceCancel();
            }

            return forceCancel;
        }
    }
}

registry.category("pos_payment_providers").add("bancontact_pay", PaymentBancontact);
