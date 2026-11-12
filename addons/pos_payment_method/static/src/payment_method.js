import { BusPlugin } from "@bus/services/bus_plugin";
import { usePlugin, Registry, t, signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ORM } from "@web/core/orm_plugin";

/**
 * @typedef {{
 *   status: "paid";
 *   transaction_id: string;
 *   card_no?: string;
 *   card_type?: string;
 *   card_brand?: string;
 * } | {
 *   status: "failed";
 *   transaction_id: string;
 *   error?: string;
 * }} TransactionCompleteResponse
 *
 * @typedef {TransactionCompleteResponse | {
 *   status: "pending";
 *   transaction_id: string;
 * }} TransactionStatusResponse
 */

export class PaymentMethod {
    constructor() {
        this.setup(...arguments);
    }

    /** @param {number} electronicPaymentId */
    setup(electronicPaymentId) {
        this.orm = usePlugin(ORM);
        this.busService = usePlugin(BusPlugin);
        this.id = electronicPaymentId;
        this.busService.addChannel("pos.electronic.payment:" + this.id);
        this.busService.subscribe("pos.electronic.payment", this._handlePaymentResponse.bind(this));

        /** @type {Record<string, number>} */
        this.intervalIds = {};
        /** @type {Record<string, (result: TransactionCompleteResponse) => void>} */
        this.transactionCallbacks = {};
        this.status = signal("");
    }

    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return false;
    }

    pollingIntervalMs() {
        return 0;
    }

    /** @param {TransactionCompleteResponse} response */
    _handlePaymentResponse(response) {
        if (response.transaction_id in this.transactionCallbacks) {
            if (!["paid", "failed"].includes(response.status)) {
                console.warn(`Invalid payment status received, ignoring: ${response.status}`);
                return;
            }
            this.transactionCallbacks[response.transaction_id](response);
        }
    }

    /**
     * @param {TransactionStatusResponse} response
     * @param {(result: TransactionCompleteResponse) => void} onTransactionComplete
     */
    _handleTransactionResponse(response, onTransactionComplete) {
        if ("error" in response) {
            throw new Error(response.error);
        }

        if (response.status !== "pending") {
            onTransactionComplete(response);
            return response;
        }

        this.startListening(response.transaction_id, onTransactionComplete);
        return response;
    }

    /** @param {string} transactionId */
    _poll(transactionId) {
        if (this.intervalIds[transactionId]) {
            throw new Error("Polling already in progress for this transaction");
        }

        this.intervalIds[transactionId] = setInterval(async () => {
            const result = await this.getTransactionStatus(transactionId).catch((error) => {
                console.warn("Error from Odoo whilst polling payment: " + error.message);
            });
            if (!result || result.status === "pending" || !this.intervalIds[transactionId]) {
                return;
            }
            if (result.error && !result.status) {
                console.warn("Error from payment provider whilst polling payment: " + result.error);
                return;
            }
            this._handlePaymentResponse(result);
        }, this.pollingIntervalMs());
    }

    /**
     * @param {string} method
     * @param {unknown[]} args
     */
    async _callPaymentMethod(method, ...args) {
        return await this.orm.call("pos.electronic.payment", method, [this.id, ...args]);
    }

    async _initPaymentMethod() {
        return await this._callPaymentMethod("init_payment_method");
    }

    /**
     * @param {number} amount
     * @param {number} currencyId
     * @param {Record<string, unknown> | null} extraArgs
     * @param {(result: TransactionCompleteResponse) => void} onPaymentComplete
     */
    async startPayment(amount, currencyId, extraArgs, onPaymentComplete) {
        const response = await this._callPaymentMethod(
            "start_payment",
            amount,
            currencyId,
            extraArgs
        );
        return this._handleTransactionResponse(response, onPaymentComplete);
    }

    /**
     * @param {number} amount
     * @param {number} currencyId
     * @param {string} originalTransactionId
     * @param {Record<string, unknown> | null} extraArgs
     * @param {(result: TransactionCompleteResponse) => void} onReversalComplete
     */
    async startReversal(amount, currencyId, originalTransactionId, extraArgs, onReversalComplete) {
        if (!this.supportsReversals()) {
            throw new Error(_t("This payment method does not support reversing payments."));
        }

        const response = await this._callPaymentMethod(
            "start_reversal",
            amount,
            currencyId,
            originalTransactionId,
            extraArgs
        );
        return this._handleTransactionResponse(response, onReversalComplete);
    }

    /**
     * @param {number} amount
     * @param {number} currencyId
     * @param {Record<string, unknown> | null} extraArgs
     * @param {(result: TransactionCompleteResponse) => void} onRefundComplete
     */
    async startRefund(amount, currencyId, extraArgs, onRefundComplete) {
        if (!this.supportsRefunds()) {
            throw new Error(_t("This payment method does not support unreferenced refunds."));
        }
        const response = await this._callPaymentMethod(
            "start_refund",
            amount,
            currencyId,
            extraArgs
        );
        return this._handleTransactionResponse(response, onRefundComplete);
    }

    /**
     * @param {number} amount
     * @param {number} currencyId
     * @param {string} transactionId
     * @param {Record<string, unknown> | null} extraArgs
     * @param {(result: TransactionCompleteResponse) => void} onAdjustmentComplete
     */
    async adjustPayment(amount, currencyId, transactionId, extraArgs, onAdjustmentComplete) {
        const response = await this._callPaymentMethod(
            "adjust_payment",
            amount,
            currencyId,
            transactionId,
            extraArgs
        );
        return this._handleTransactionResponse(response, onAdjustmentComplete);
    }

    /**
     * @param {number} amount
     * @param {number} currencyId
     * @param {string} transactionId
     * @param {Record<string, unknown> | null} extraArgs
     * @param {(result: TransactionCompleteResponse) => void} onCaptureComplete
     */
    async capturePayment(amount, currencyId, transactionId, extraArgs, onCaptureComplete) {
        const response = await this._callPaymentMethod(
            "capture_payment",
            amount,
            currencyId,
            transactionId,
            extraArgs
        );
        return this._handleTransactionResponse(response, onCaptureComplete);
    }

    /** @param {string} transactionId */
    cancelTransaction(transactionId) {
        return this._callPaymentMethod("cancel_transaction", transactionId);
    }

    /**
     * @param {string} transactionId
     * @returns {Promise<TransactionStatusResponse>}
     */
    async getTransactionStatus(transactionId) {
        return await this._callPaymentMethod("get_transaction_status", transactionId);
    }

    /**
     * @param {string} transactionId
     * @param {(result: TransactionCompleteResponse) => void} onTransactionComplete
     */
    startListening(transactionId, onTransactionComplete) {
        /** @param {TransactionCompleteResponse} response */
        const callback = (response) => {
            this.stopListening(transactionId);
            onTransactionComplete(response);
        };
        this.transactionCallbacks[transactionId] = callback;

        if (this.pollingIntervalMs()) {
            this._poll(transactionId);
        }
    }

    /** @param {string} transactionId */
    stopListening(transactionId) {
        if (this.intervalIds[transactionId]) {
            clearInterval(this.intervalIds[transactionId]);
            delete this.intervalIds[transactionId];
        }
        if (this.transactionCallbacks[transactionId]) {
            delete this.transactionCallbacks[transactionId];
        }
    }
}

export const electronicPaymentRegistry = new Registry({
    name: "Electronic Payment Methods",
    validation: t.constructor(PaymentMethod),
});
