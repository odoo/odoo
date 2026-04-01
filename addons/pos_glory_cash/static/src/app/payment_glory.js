import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { CancelDialog } from "@pos_glory_cash/app/components/cancel_dialog";
import { GLORY_STATUS_STRING } from "@pos_glory_cash/utils/constants";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { GloryService } from "@pos_glory_cash/glory_service";

const CONNECT_TIMEOUT_MS = 5000;

export class PaymentGlory extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.dialog = this.env.services.dialog;
        this.cancellationResolver = null;
        this.gloryService = new GloryService(this.onStatusChange.bind(this));
        this.gloryService.connect(
            this.payment_method_id.glory_websocket_address,
            this.payment_method_id.glory_username,
            this.payment_method_id.glory_password
        );

        setTimeout(() => {
            if (this.gloryService.status === "DISCONNECTED") {
                this.onStatusChange("DISCONNECTED");
            }
        }, CONNECT_TIMEOUT_MS);
    }

    onStatusChange(newStatus) {
        switch (newStatus) {
            case "IDLE": {
                const isFirstStatus = this.gloryService.state.inventory.length === 0;
                if (isFirstStatus && this.paymentLine) {
                    // In this case we have a stale payment
                    this.pos.getOrder().removePaymentline(this.paymentLine);
                }
                return;
            }
            case "DISCONNECTED": {
                this.showError(
                    _t(
                        "Failed to connect to Glory cash machine, please ensure it is switched on and connected to the network."
                    )
                );
                return;
            }
            case "BAD_CREDENTIALS": {
                this.showError(
                    _t(
                        "Failed to login to Glory cash machine, please check the configured username and password."
                    )
                );
                return;
            }
            case "WAITING_ERROR_RECOVERY": {
                this.showError(this.currentErrorMessage);
                return;
            }
            case "WAITING_CANCEL": {
                if (this.paymentLine) {
                    this.showCancelDialog(
                        _t(
                            "There is insufficient change in the cash machine to handle the payment. It must be cancelled to continue."
                        )
                    );
                }
                return;
            }
        }
    }

    get status() {
        return GLORY_STATUS_STRING[this.gloryService.status] ?? this.gloryService.status;
    }

    get amountInserted() {
        return this.gloryAmountToPosAmount(this.gloryService.state.amountInserted);
    }

    get paymentLine() {
        const order = this.pos.getOrder();
        if (!order) {
            return null;
        }

        const gloryPaymentLines = order.payment_ids.filter(
            (line) => line.payment_method_id === this.payment_method_id
        );

        return gloryPaymentLines.find((line) =>
            ["waiting", "waitingCancel"].includes(line.payment_status)
        );
    }

    getDenominationsWithStatus(status) {
        return this.gloryService.state.inventory
            .filter((denomination) => denomination.status === status)
            .map((denomination) => ({
                ...denomination,
                value: this.gloryAmountToPosAmount(denomination.value),
            }));
    }

    get currentErrorMessage() {
        if (
            this.gloryService.status !== "ERROR" &&
            this.gloryService.status !== "WAITING_ERROR_RECOVERY"
        ) {
            return null;
        }
        return (
            this.gloryService.state.lastDeviceError ??
            _t("The cash machine has an error, please consult its display for details.")
        );
    }

    async sendPaymentRequest() {
        if (!this.paymentLine) {
            return false;
        }

        if (this.paymentLine.amount < 0 && this.pos.getCashier()._role !== "manager") {
            this.showError(_t("Only managers can withdraw cash from the cash machine."));
            return false;
        }

        const amountInCents = Math.round(
            this.paymentLine.amount * Math.pow(10, this.pos.currency.decimal_places)
        );
        const paymentResult = await this.gloryService.sendPaymentRequest(amountInCents);

        if (!this.paymentLine) {
            console.warn("Glory payment response received, but no payment in progress");
            return false;
        }

        if (this.cancellationResolver) {
            this.cancellationResolver();
            this.cancellationResolver = null;
        }

        switch (paymentResult.status) {
            case "DISCONNECTED":
            case "BAD_CREDENTIALS": {
                this.showError(_t("The cash machine is disconnected."));
                return false;
            }
            case "ERROR":
            case "WAITING_ERROR_RECOVERY": {
                this.showError(this.currentErrorMessage);
                return false;
            }
            case "COLLECTING":
            case "WAITING_REPLENISHMENT": {
                this.showError(
                    _t(
                        "The cash machine is currently in collection/replenishment mode, please finish this process on the machine before making a payment."
                    )
                );
                return false;
            }
            case "SUCCESS": {
                this.setPaymentInfo(paymentResult, true);
                return true;
            }
            case "CHANGE_SHORTAGE":
                this.setPaymentInfo(paymentResult, false);
                await this.pos.printReceipt({ printBillActionTriggered: true });
                this.showError(_t("There is insufficient cash in the machine to give change."));
                return false;
            case "OCCUPIED_BY_OTHER":
                this.showError(_t("The cash machine is in use by another POS."));
                return false;
            case "EXCLUSIVE_ERROR": {
                this.showCancelDialog(
                    _t("The cash machine is busy with another operation. Do you want to cancel it?")
                );
                return false;
            }
            case "AUTO_RECOVERY_FAILURE": {
                this.showError(
                    _t(
                        "The payment failed due to an unrecoverable error - see the cash machine screen for details."
                    )
                );
                return false;
            }
            case "CANCEL": {
                return false;
            }
            default: {
                this.showError(
                    _t("The payment failed for an unknown reason: %s", paymentResult.status)
                );
                return false;
            }
        }
    }

    async sendPaymentCancel() {
        const cancelResult = await this.gloryService.initiatePaymentCancel();

        if (cancelResult === "DISCONNECTED") {
            this.showError(_t("The cash machine is disconnected."));
            return false;
        }

        const cancelPromise = new Promise((resolve) => {
            this.cancellationResolver = resolve;
        });
        return await cancelPromise;
    }

    /**
     * @param {{ status: string, cashGiven?: number, cashReturned?: number, transactionId?: string }} paymentResponse
     */
    setPaymentInfo(paymentResponse) {
        const isSuccessful = paymentResponse.status === "SUCCESS";
        const { transactionId, cashGiven, cashReturned } = paymentResponse;
        this.paymentLine.transaction_id = transactionId;
        this.paymentLine.setAmount(this.gloryAmountToPosAmount(cashGiven));
        this.paymentLine.setReceiptInfo(
            this.makeReceiptMessage(transactionId, cashGiven, cashReturned, isSuccessful)
        );
    }

    /**
     * @param {string} transactionId
     * @param {number} amountDeposited
     * @param {number} amountReturned
     * @param {boolean} isSuccessful
     * @returns {string}
     */
    makeReceiptMessage(transactionId, amountDeposited, amountReturned, isSuccessful) {
        const header = isSuccessful
            ? _t("GLORY TRANSACTION SUCCESSFUL")
            : _t("GLORY TRANSACTION CANCELLED");
        const transactionIdLine = _t("Transaction ID: %s", transactionId);
        const depositedLine = _t(
            "Cash deposited: %s",
            this.env.utils.formatCurrency(this.gloryAmountToPosAmount(amountDeposited))
        );
        const changeGivenLine = _t(
            "Change given: %s",
            this.env.utils.formatCurrency(this.gloryAmountToPosAmount(amountReturned))
        );

        return `${header}\n${transactionIdLine}\n${depositedLine}\n${changeGivenLine}\n\n`;
    }

    gloryAmountToPosAmount(amountInCents) {
        const amount = amountInCents / Math.pow(10, this.pos.currency.decimal_places);
        return this.env.utils.roundCurrency(amount);
    }

    showError(msg, title) {
        if (!title) {
            title = _t("Cash Machine Error");
        }
        this.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }

    showCancelDialog(message) {
        this.dialog.add(CancelDialog, {
            message,
            cancel: async () => {
                const cancelStatus = await this.gloryService.initiatePaymentCancel();
                if (
                    cancelStatus !== "SUCCESS" &&
                    !["IDLE", "RESETTING"].includes(this.gloryService.status)
                ) {
                    await this.gloryService.reset();
                }
            },
        });
    }
}
