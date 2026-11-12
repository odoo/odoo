import { GloryService } from "@pos_payment_method_glory/utils/glory_service";
import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";
import { signal, usePlugin } from "@odoo/owl";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { GloryErrorDialog } from "@pos_payment_method_glory/components/glory_error_dialog";
import { CancelDialog } from "@pos_payment_method_glory/components/cancel_dialog";
import { GLORY_STATUS_STRING } from "./utils/constants";

const CONNECT_TIMEOUT_MS = 5000;
const LOCAL_STORAGE_KEY = "pos_payment_method_glory.currency_decimals";

const ERROR_MESSAGES = {
    DISCONNECTED: _t(
        "Failed to connect to Glory cash machine, please ensure it is switched on and connected to the network."
    ),
    BAD_CREDENTIALS: _t(
        "Failed to login to Glory cash machine, please check the configured username and password."
    ),
    WAITING_CANCEL: _t(
        "There is insufficient change in the cash machine to handle the payment. It must be cancelled to continue."
    ),
    CHANGE_SHORTAGE: _t(
        "There is insufficient cash in the machine to give change. You will need to refund the difference via another method."
    ),
    CANCEL_CHANGE_SHORTAGE: _t(
        "The cash machine is unable to return the inserted cash, please refund the client via another method."
    ),
    WAITING_CASH_OUT_REMOVE: _t(
        "Please remove the cash from the exit of the cash machine before starting a transaction."
    ),
    WAITING_CASH_IN_REMOVE: _t(
        "Please remove the cash from the input of the cash machine before starting a transaction."
    ),
    WAITING_INVENTORY: _t(
        "The cash machine is busy counting its inventory, please wait a few seconds and retry."
    ),
    ERROR: _t("The cash machine has an error, please consult its display for details."),
    WAITING_ERROR_RECOVERY: _t(
        "The cash machine has an error, please consult its display for details."
    ),
    COLLECTING: _t(
        "The cash machine is currently in collection mode, please finish this process on the machine before making a payment."
    ),
    WAITING_REPLENISHMENT: _t(
        "The cash machine is currently in replenishment mode, please finish this process on the machine before making a payment."
    ),
    OCCUPIED_BY_OTHER: _t("The cash machine is in use by another POS."),
    EXCLUSIVE_ERROR: _t(
        "The cash machine is busy with another operation. Do you want to cancel it?"
    ),
    EXCLUSIVE_ERROR_IDLE: _t(
        "The cash machine is not ready to start a transaction. Check all the covers are closed and then try again."
    ),
    AUTO_RECOVERY_FAILURE: _t(
        "The payment failed due to an unrecoverable error - see the cash machine screen for details."
    ),
};

export class PaymentMethodGlory extends PaymentMethod {
    supportsRefunds() {
        return true;
    }

    supportsReversals() {
        return false;
    }

    pollingIntervalMs() {
        return 0;
    }

    setup() {
        super.setup(...arguments);
        this.dialog = usePlugin(DialogPlugin);
        this.gloryService = new GloryService(this._onStatusChange.bind(this));
        this.closeErrorDialog = null;
        this.currencyDecimals = parseInt(
            window.localStorage.getItem("pos_payment_method_glory.currency_decimals")
        );
        this.statusString = signal(GLORY_STATUS_STRING["DISCONNECTED"]);
    }

    showError(message) {
        this.dialog.add(AlertDialog, {
            title: _t("Cash Machine Error"),
            body: message,
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

    async _connectToGloryMachine() {
        if (this.connectPromise) {
            if (this.gloryService.status !== "DISCONNECTED") {
                return;
            }
            return await this.connectPromise.promise;
        }
        this.connectPromise = Promise.withResolvers();
        const { glory_ip, glory_username, glory_password, glory_use_lna } =
            await this._initPaymentMethod();
        this.gloryService.connect(glory_ip, glory_username, glory_password, glory_use_lna);
        setTimeout(() => {
            this.connectPromise.reject(new Error(ERROR_MESSAGES.DISCONNECTED));
        }, CONNECT_TIMEOUT_MS);
        await this.connectPromise.promise;
    }

    _onStatusChange(newStatus) {
        this.statusString.set(GLORY_STATUS_STRING[newStatus] ?? newStatus);
        this.connectPromise.resolve();
        if (this.closeErrorDialog && !["ERROR", "WAITING_ERROR_RECOVERY"].includes(newStatus)) {
            this.closeErrorDialog();
            this.closeErrorDialog = null;
        }

        switch (newStatus) {
            case "IDLE": {
                for (const callback of Object.values(this.transactionCallbacks)) {
                    callback({ status: "failed" });
                }
                return;
            }
            case "WAITING_ERROR_RECOVERY": {
                if (this.gloryService.state.errorGif) {
                    this.closeErrorDialog = this.dialog.add(GloryErrorDialog, {
                        errorCode: this.gloryService.state.errorCode,
                        errorGif: this.gloryService.state.errorGif,
                        reset: () => this.gloryService.reset(),
                    });
                }
                return;
            }
            case "WAITING_CANCEL": {
                this.showCancelDialog(ERROR_MESSAGES.WAITING_CANCEL);
                return;
            }
            case "DISCONNECTED": {
                this.showError(ERROR_MESSAGES.DISCONNECTED);
                return;
            }
        }
    }

    _getErrorMessage(status) {
        if (["IDLE", "CANCEL", "SUCCESS"].includes(status)) {
            return null;
        }
        return ERROR_MESSAGES[status] ?? _t("The payment failed for an unknown reason: %s", status);
    }

    _getStartPaymentError(result) {
        if (["ERROR", "WAITING_ERROR_RECOVERY"].includes(result.status)) {
            if (result.specialDeviceError) {
                return result.specialDeviceError;
            }
            if (result.billDeviceStatus !== "STATE_IDLE") {
                return _t("The bill device is in an error state: %s", result.billDeviceStatus);
            }
            if (result.coinDeviceStatus !== "STATE_IDLE") {
                return _t("The coin device is in an error state: %s", result.coinDeviceStatus);
            }
        }
        return this._getErrorMessage(result.status);
    }

    /**
     * @param {Record<string, string>} result
     * @param {(result: any) => void} onPaymentComplete
     */
    async _handleGloryPaymentResponse(result, transactionId) {
        if (["SUCCESS", "CHANGE_SHORTAGE", "CANCEL_CHANGE_SHORTAGE"].includes(result.status)) {
            if (result.status !== "SUCCESS") {
                this.showError(ERROR_MESSAGES[result.status]);
            }
            if (result.cashGiven === 0 && result.cashReturned === 0) {
                return this._handlePaymentResponse({
                    transaction_id: transactionId,
                    status: "failed",
                });
            }
            return this._handlePaymentResponse({
                transaction_id: transactionId,
                status: "paid",
                final_transaction_id: result.transactionId,
                final_amount: this._convertCurrencyUnitsToDecimal(
                    result.cashGiven - result.cashReturned
                ),
            });
        } else if (result.status === "EXCLUSIVE_ERROR") {
            if (this.gloryService.status === "IDLE") {
                return this._handlePaymentResponse({
                    transaction_id: transactionId,
                    status: "failed",
                    error: ERROR_MESSAGES.EXCLUSIVE_ERROR_IDLE,
                });
            } else {
                this.showCancelDialog(ERROR_MESSAGES.EXCLUSIVE_ERROR);
            }
        } else {
            return this._handlePaymentResponse({
                transaction_id: transactionId,
                status: "failed",
                error: this._getErrorMessage(result.status),
            });
        }
    }

    async _startGloryTransaction(backendResult) {
        this.currencyDecimals = backendResult.currency_decimals;
        window.localStorage.setItem(LOCAL_STORAGE_KEY, this.currencyDecimals);
        const startPaymentResult = await this.gloryService.startPayment(
            backendResult.amount_units,
            backendResult.transaction_id
        );
        if (startPaymentResult.status !== "SUCCESS") {
            this._handlePaymentResponse({
                ...backendResult,
                status: "failed",
                error: this._getStartPaymentError(startPaymentResult),
            });
        }

        return backendResult;
    }

    _convertCurrencyUnitsToDecimal(amountUnits) {
        return amountUnits / Math.pow(10, this.currencyDecimals || 0);
    }

    async startPayment() {
        await this._connectToGloryMachine();
        const result = await super.startPayment(...arguments);
        return this._startGloryTransaction(result);
    }

    async startRefund() {
        await this._connectToGloryMachine();
        const result = await super.startRefund(...arguments);
        return this._startGloryTransaction(result);
    }

    async startListening(transactionId) {
        super.startListening(...arguments);
        await this._connectToGloryMachine();
        this.gloryService.waitForPaymentResponse(transactionId).then((result) => {
            this._handleGloryPaymentResponse(result, transactionId);
        });
    }

    async cancelTransaction() {
        const cancelResult = await this.gloryService.initiatePaymentCancel();
        if (cancelResult !== "SUCCESS") {
            if (cancelResult === "EXCLUSIVE_ERROR") {
                this.showCancelDialog(ERROR_MESSAGES.EXCLUSIVE_ERROR);
                return { success: false };
            }
            return { error: this._getErrorMessage(cancelResult) };
        }
        return {};
    }

    get amountInserted() {
        return this._convertCurrencyUnitsToDecimal(this.gloryService.state.amountInserted);
    }
}

electronicPaymentRegistry.add("glory", PaymentMethodGlory);
