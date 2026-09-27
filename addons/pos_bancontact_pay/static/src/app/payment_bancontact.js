import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PaymentBancontact extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.supports_refunds = false;
    }

    async sendPaymentRequest(line) {
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
