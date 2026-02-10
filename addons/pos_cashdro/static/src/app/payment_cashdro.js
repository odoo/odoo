import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { CashdroService } from "@pos_cashdro/cashdro_service";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class PaymentCashdro extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;
        this.cashdroService = new CashdroService();
        this.cashdroService.connect(
            this.payment_method_id.cashdro_ip,
            this.payment_method_id.cashdro_username,
            this.payment_method_id.cashdro_password,
            this.payment_method_id.cashdro_use_lna
        );

        this.resumePaymentInProgress();
    }

    /** @returns {import("@point_of_sale/app/models/pos_payment").PosPayment | null} */
    get paymentLine() {
        const order = this.pos.getOrder();
        if (!order) {
            return null;
        }

        const cashdroPaymentLines = order.payment_ids.filter(
            (line) => line.payment_method_id === this.payment_method_id
        );

        return cashdroPaymentLines.find((line) =>
            ["waiting", "waitingCancel"].includes(line.payment_status)
        );
    }

    /** @returns {string | null} */
    get operationId() {
        return this.paymentLine?.uiState?.cashdroOperationId ?? null;
    }

    get amountInserted() {
        return this.cashdroAmountToPosAmount(this.cashdroService.state.amountInserted);
    }

    async resumePaymentInProgress() {
        // A small delay allows the POS to finish loading
        await new Promise((resolve) => setTimeout(resolve, 100));

        if (this.operationId) {
            const isPaymentSuccessful = await this.waitForPaymentResponse();
            this.paymentLine.handlePaymentResponse(isPaymentSuccessful);
        }
    }

    async isOperationAlreadyExecuting() {
        const executingOperationId = await this.cashdroService
            .getCurrentlyExecutingOperation()
            .catch((error) => this.showError(_t("Cashdro error: %s", error.message)));
        if (!executingOperationId) {
            return executingOperationId !== null;
        }

        const shouldCancel = await ask(this.pos.dialog, {
            title: _t("Cashdro machine is busy"),
            body: _t(
                "The cash machine is busy with another operation. Do you want to cancel it and retry?"
            ),
            confirmLabel: _t("Yes"),
            cancelLabel: _t("No"),
        });
        if (shouldCancel) {
            try {
                await this.cashdroService.cancelPayment(executingOperationId);
                await this.cashdroService.waitForPaymentCompletion(executingOperationId);
                return false;
            } catch {
                this.showError(_t("Cancellation failed"));
            }
        }

        return true;
    }

    async waitForPaymentResponse() {
        const paymentResult = await this.cashdroService
            .waitForPaymentCompletion(this.operationId)
            .catch((error) => this.showError(_t("Cashdro payment failed: %s", error.message)));
        if (!this.paymentLine || !paymentResult) {
            return false;
        }

        const { totalin, totalout, operationid } = paymentResult.operation;
        const moneyIn = this.cashdroAmountToPosAmount(totalin);
        const moneyOut = Math.abs(this.cashdroAmountToPosAmount(totalout));
        const netAmount = this.env.utils.roundCurrency(moneyIn - moneyOut);
        if (netAmount == 0) {
            // Payment was cancelled
            return false;
        }
        if (this.paymentLine.pos_order_id.remainingDue === 0 && this.paymentLine.amount > 0) {
            // In this case, the POS will automatically add the 'Change' line
            this.paymentLine.setAmount(moneyIn);
        } else {
            this.paymentLine.setAmount(netAmount);
        }
        this.paymentLine.transaction_id = operationid;

        return true;
    }

    async sendPaymentRequest() {
        if (!this.paymentLine || (await this.isOperationAlreadyExecuting())) {
            return false;
        }

        const amountInCents = Math.round(
            this.paymentLine.amount * Math.pow(10, this.pos.currency.decimal_places)
        );
        const operationId = await this.cashdroService
            .sendPaymentRequest(amountInCents)
            .catch(async (error) => {
                this.showError(_t("Cashdro payment failed: %s", error.message));
            });

        if (!this.paymentLine || !operationId) {
            return false;
        }

        this.paymentLine.uiState = {
            ...(this.paymentLine.uiState ?? {}),
            cashdroOperationId: operationId,
        };
        return this.waitForPaymentResponse(operationId);
    }

    async sendPaymentCancel() {
        if (!this.operationId) {
            return true;
        }

        await this.cashdroService.cancelPayment(this.operationId).catch((error) => {
            this.showError(_t("Cashdro cancellation failed: %s", error.message));
        });
        // Don't resolve the cancellation, we want to wait
        return new Promise(() => {});
    }

    /**
     * @param {string | number} amountInCents
     * @returns {number}
     */
    cashdroAmountToPosAmount(amountInCents) {
        if (typeof amountInCents === "string") {
            amountInCents = parseInt(amountInCents);
        }
        const amount = amountInCents / Math.pow(10, this.pos.currency.decimal_places);
        return this.env.utils.roundCurrency(amount);
    }

    /** @param {string} message */
    showError(message) {
        this.dialog.add(AlertDialog, {
            title: _t("Cash Machine Error"),
            body: message,
        });
    }
}
