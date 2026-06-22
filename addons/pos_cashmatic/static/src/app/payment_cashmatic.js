import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { CashmaticService } from "@pos_cashmatic/cashmatic_service";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class PaymentCashmatic extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;
        this.cashmaticService = new CashmaticService();
        this.cashmaticService.connect(
            this.payment_method_id.cashmatic_ip,
            this.payment_method_id.cashmatic_username,
            this.payment_method_id.cashmatic_password,
            this.payment_method_id,
            this.pos.lnaFallback
        );
    }

    get paymentLine() {
        const order = this.pos.getOrder();
        if (!order) {
            return null;
        }

        const cashmaticPaymentLines = order.payment_ids.filter(
            (line) => line.payment_method_id === this.payment_method_id
        );

        return cashmaticPaymentLines.find((line) =>
            ["waiting", "waitingCancel"].includes(line.payment_status)
        );
    }

    async sendPaymentRequest() {
        if (!this.paymentLine) {
            return false;
        }

        this.cancelling = false;
        const amountInCents = Math.round(
            this.paymentLine.amount * Math.pow(10, this.pos.currency.decimal_places)
        );
        const reference = this.pos.getOrder().name;
        let notDispensed;
        try {
            if (amountInCents < 0) {
                notDispensed = await this.cashmaticService.sendWithdrawalRequest(
                    Math.abs(amountInCents),
                    reference
                );
            } else {
                notDispensed = await this.cashmaticService.sendPaymentRequest(
                    amountInCents,
                    reference
                );
            }
        } catch (error) {
            this.showError(_t("Cashmatic payment failed: %s", error.message));
            return false;
        }

        if (this.cancelling) {
            return false;
        }

        if (notDispensed > 0) {
            this.showError(
                _t(
                    "The cash machine could not dispense %s. Please give the remaining amount to the customer manually.",
                    this.env.utils.formatCurrency(this.cashmaticAmountToPosAmount(notDispensed))
                )
            );
        }
        return true;
    }

    async sendPaymentCancel() {
        const success = await this.cashmaticService
            .cancelCurrentPayment()
            .then(() => {
                this.cancelling = true;
                return true;
            })
            .catch((error) => {
                this.showError(_t("Cashmatic cancellation failed: %s", error.message));
                return false;
            });
        return success;
    }

    get amountInserted() {
        return this.cashmaticAmountToPosAmount(this.cashmaticService.state.amountInserted);
    }

    get amountDispensed() {
        return this.cashmaticAmountToPosAmount(this.cashmaticService.state.amountDispensed);
    }

    cashmaticAmountToPosAmount(amountInCents) {
        const amount = amountInCents / Math.pow(10, this.pos.currency.decimal_places);
        return this.env.utils.roundCurrency(amount);
    }

    showError(message) {
        this.dialog.add(AlertDialog, {
            title: _t("Cash Machine Error"),
            body: message,
        });
    }
}
