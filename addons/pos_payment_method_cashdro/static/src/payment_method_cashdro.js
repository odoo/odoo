import { Logger } from "@bus/workers/bus_worker_utils";
import { usePlugin } from "@odoo/owl";
import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { getCurrency } from "@web/core/currency";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { _t } from "@web/core/l10n/translation";

const CASHDRO_URL = "/Cashdro3WS/index3.php";
const OPERATION_STATE = {
    INIT: "I",
    QUEUED: "Q",
    EXECUTING: "E",
    FINISHED: "F",
};
const SUCCESS_RESULT_CODE = 1;
const TRANSACTION_TYPE_PAYMENT = 4;
const TRANSACTION_TYPE_REFUND = 3;
const FINALIZE_TYPE_CANCEL = 2;

export class PaymentMethodCashdro extends PaymentMethod {
    supportsRefunds() {
        return true;
    }

    supportsReversals() {
        return false;
    }

    supportsBackendConfirmation() {
        return false;
    }

    pollingIntervalMs() {
        return 3000;
    }

    setup() {
        super.setup(...arguments);
        this.dialog = usePlugin(DialogPlugin);
        this.logger = new Logger("pos_cashdro");
    }

    async _initPaymentMethod() {
        if (!this.cashdroSettings) {
            this.cashdroSettings = await super._initPaymentMethod();
        }
    }

    /**
     * @param {string} operation
     * @param {Record<string, string>} [params]
     * @returns {Promise<Record<string, unknown>>}
     */
    async _cashdroRequest(operation, params = {}) {
        const protocol = this.cashdroSettings.cashdro_use_lna ? "http:" : window.location.protocol;
        const queryParams = new URLSearchParams({
            operation,
            name: this.cashdroSettings.cashdro_username,
            password: this.cashdroSettings.cashdro_password,
            ...params,
        });
        const url = `${protocol}//${this.cashdroSettings.cashdro_ip}${CASHDRO_URL}?${queryParams}`;
        this._cashdroLog("REQUEST", url);

        try {
            const response = await fetch(url, {
                targetAddressSpace: this.forceHttp ? "local" : undefined,
                signal: AbortSignal.timeout(10000),
            });

            if (!response.ok) {
                this._cashdroLog("HTTP ERROR", `${url}: ${response.status}`);
                throw new Error(response.statusText);
            }
            const cashdroResult = await response.json();
            this._cashdroLog("RESPONSE", cashdroResult);
            if (cashdroResult.code !== SUCCESS_RESULT_CODE) {
                throw new Error(cashdroResult.response.errorMessage);
            }

            return cashdroResult.response;
        } catch (error) {
            if (error instanceof TypeError) {
                this._cashdroLog("NETWORK ERROR", error.message);
                throw new Error(
                    _t(
                        "Could not reach cash machine on the network, please check your IP and/or LNA settings."
                    )
                );
            }
            throw error;
        }
    }

    async _cashdroCheckIfMachineIsBusy(isKiosk) {
        const { operation } = await this._cashdroRequest("askOperationExecuting");
        const currentOperationId = operation?.OperationId;
        if (!currentOperationId) {
            return false;
        }

        if (isKiosk) {
            this.dialog.add(AlertDialog, {
                title: _t("Cash Machine Error"),
                body: _t(
                    "The cash machine is busy with another payment, please wait until it is free."
                ),
            });
            return true;
        }

        const cancelPromise = Promise.withResolvers();
        this.dialog.add(
            ConfirmationDialog,
            {
                title: _t("Cashdro machine is busy"),
                body: _t(
                    "The cash machine is busy with another operation. Do you want to cancel it?"
                ),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
                confirm: () => cancelPromise.resolve(true),
                cancel: () => cancelPromise.resolve(false),
            },
            {
                onClose: () => cancelPromise.resolve(false),
            }
        );
        if (await cancelPromise.promise) {
            await this.cancelTransaction(currentOperationId);
        }

        return true;
    }

    async _startCashdroTransaction(
        amount,
        currencyId,
        operationType,
        onTransactionComplete,
        isKiosk = false
    ) {
        await this._initPaymentMethod();
        const currencyDigits = getCurrency(currencyId).digits[1];
        const amountInCents = Math.round(amount * Math.pow(10, currencyDigits));

        if (await this._cashdroCheckIfMachineIsBusy(isKiosk)) {
            return this._handleTransactionResponse({ status: "failed" }, onTransactionComplete);
        }

        const response = await this._cashdroRequest("startOperation", {
            type: operationType,
            parameters: JSON.stringify({ amount: amountInCents.toString() }),
        });
        const operationId = response.operation.operationId;
        await this._cashdroRequest("acknowledgeOperationId", { operationId });

        return this._handleTransactionResponse(
            { transaction_id: `${operationId}/${currencyId}`, status: "pending" },
            onTransactionComplete
        );
    }

    /**
     * @param {string} message
     * @param {any} payload
     */
    _cashdroLog(message, payload) {
        this.logger.log(
            `${luxon.DateTime.now().toFormat("yyyy-LL-dd HH:mm:ss")} ${message}: ${JSON.stringify(
                payload
            )}`
        );
    }

    async startPayment(amount, currencyId, extraArgs, onPaymentComplete) {
        this.amountInserted.set(0);
        const isKiosk = "kiosk_order_id" in extraArgs;
        return this._startCashdroTransaction(
            amount,
            currencyId,
            TRANSACTION_TYPE_PAYMENT,
            onPaymentComplete,
            isKiosk
        );
    }

    async startRefund(amount, currencyId, _extraArgs, onRefundComplete) {
        return this._startCashdroTransaction(
            amount,
            currencyId,
            TRANSACTION_TYPE_REFUND,
            onRefundComplete
        );
    }

    async cancelTransaction(transactionId) {
        const operationId = transactionId.split("/")[0];
        await this._cashdroRequest("finishOperation", { operationId, type: FINALIZE_TYPE_CANCEL });
        return {};
    }

    async getTransactionStatus(transactionId) {
        await this._initPaymentMethod();
        const [operationId, currencyId] = transactionId.split("/");
        const currencyDigits = getCurrency(currencyId).digits[1];
        const { operation } = await this._cashdroRequest("askOperation", { operationId });

        const amountInsertedInCents = parseInt(operation.operation.totalin);
        if (amountInsertedInCents > 0) {
            this.amountInserted.set(amountInsertedInCents / Math.pow(10, currencyDigits));
        }

        if (operation.operation.state !== OPERATION_STATE.FINISHED) {
            return { transaction_id: transactionId, status: "pending" };
        }

        this.amountInserted.set(null);
        const { totalin, totalout } = operation.operation;
        const moneyIn = parseInt(totalin);
        const moneyOut = Math.abs(parseInt(totalout));
        const netAmount = moneyIn - moneyOut;

        if (netAmount == 0) {
            return { transaction_id: transactionId, status: "failed" };
        }
        return {
            transaction_id: transactionId,
            final_amount: netAmount / Math.pow(10, currencyDigits),
            status: "paid",
        };
    }
}

electronicPaymentRegistry.add("cashdro", PaymentMethodCashdro);
