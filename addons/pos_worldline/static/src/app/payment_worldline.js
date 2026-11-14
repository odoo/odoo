import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { delay } from "@web/core/utils/concurrency";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

export class PaymentWorldline extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
        // Payment line uuid -> resolver of a cancellation
        this.cancelResolvers = {};
        // Payment line uuid -> promise of a transaction
        this.resumedPayments = {};

        this.pos.data.connectWebSocket("WORLDLINE_API_PAYMENT_STATUS", (payload) => {
            if (payload.pos_session_id !== this.pos.session.id) {
                return;
            }
            const paymentLine = this.pos.models["pos.payment"].getBy("uuid", payload.payment_uuid);
            if (paymentLine && this._isPending(paymentLine)) {
                this.handleWorldlineStatusResponse(paymentLine, payload);
            }
        });

        this._resumePendingTransactions();
    }

    /**
     * Keep listening for payment confirmations after web page refresh
     */
    _resumePendingTransactions() {
        const pendingLines = this.pos.models["pos.payment"].filter(
            (line) =>
                line.payment_method_id?.id === this.payment_method_id.id &&
                line.uiState?.worldlineExchangeId &&
                this._isPending(line)
        );
        for (const paymentLine of pendingLines) {
            this.resumedPayments[paymentLine.uuid] = this._trackTransaction(paymentLine).then(
                (success) => {
                    delete this.resumedPayments[paymentLine.uuid];
                    return paymentLine.handlePaymentResponse(success);
                }
            );
        }
    }

    _isPending(paymentLine) {
        return !paymentLine.isDone() && paymentLine.getPaymentStatus() !== "retry";
    }

    async sendPaymentRequest(uuid) {
        await super.sendPaymentRequest(...arguments);
        const line = this.pos.getOrder().getPaymentlineByUuid(uuid);
        return this._createWorldlineTransaction(line, line.amount >= 0 ? "CardPayment" : "Refund");
    }

    async _createWorldlineTransaction(paymentLine, transactionType) {
        try {
            const data = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "worldline_create_transaction",
                [
                    [paymentLine.payment_method_id.id],
                    transactionType,
                    Math.abs(paymentLine.amount),
                    paymentLine.uuid,
                    this.pos.session.id,
                ]
            );
            // Transaction failure/cancellation/etc.
            if (data.error) {
                this._showWorldlineError(data.error);
                return false;
            }
            // Stored in uiState so it is persisted in IndexedDB and the transaction
            // can still be cancelled after a page refresh.
            paymentLine.uiState.worldlineExchangeId = data.exchange_id;
            paymentLine.setPaymentStatus("waitingCard");
            return this._trackTransaction(paymentLine);
        } catch (error) {
            this._showWorldlineError(error);
            return false;
        }
    }

    async sendPaymentCancel(order, uuid) {
        const paymentLine = order.getPaymentlineByUuid(uuid);
        const exchangeId = paymentLine.uiState.worldlineExchangeId;
        if (!exchangeId) {
            this._showWorldlineError(
                "Cannot cancel a Worldline payment line without an exchange ID with uuid " + uuid
            );
            this._popPaymentResolver(paymentLine)?.(false);
            return true;
        }
        try {
            const data = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "worldline_cancel_transaction",
                [
                    [paymentLine.payment_method_id.id],
                    exchangeId,
                    paymentLine.uuid,
                    this.pos.session.id,
                ]
            );
            if (data.error) {
                this._showWorldlineError(data.error);
                return false;
            }
        } catch (error) {
            this._showWorldlineError(error);
            return false;
        }
        // It's impossible to confirm a cancellation sent from PoS by status polling
        // We cannot rely on 200 OK abort endpoint response so the only way to confirm this is through the webhook
        const { promise, resolve } = Promise.withResolvers();
        this.cancelResolvers[uuid] = resolve;
        return promise;
    }

    /**
     * Settle the promises still pending for a payment line set to "retry" without any Worldline response
     * (ex: "Force Cancel"), otherwise the payment screen keeps waiting for the terminal payment.
     */
    releasePendingTransaction(paymentLine) {
        this._popCancelResolver(paymentLine)?.(true);
        this._popPaymentResolver(paymentLine)?.(false);
    }

    _popPaymentResolver(paymentLine) {
        const resolver = this.paymentLineResolvers[paymentLine.uuid];
        delete this.paymentLineResolvers[paymentLine.uuid];
        return resolver;
    }

    _popCancelResolver(paymentLine) {
        const resolver = this.cancelResolvers[paymentLine.uuid];
        delete this.cancelResolvers[paymentLine.uuid];
        return resolver;
    }

    /**
     * Wait for the outcome of the transaction stored in the payment line uiState,
     * through the webhook notification or the status polling.
     */
    _trackTransaction(paymentLine) {
        const { promise, resolve } = Promise.withResolvers();
        this.paymentLineResolvers[paymentLine.uuid] = resolve;
        this._pollWorldlineStatus(paymentLine);
        return promise;
    }

    async _pollWorldlineStatus(paymentLine) {
        const exchangeId = paymentLine.uiState.worldlineExchangeId;
        // Note: there is no way to confirm a cancellation through polling
        // /status endpoint returns the same JSON before and after the cancellation ("pending")

        const deadline = Date.now() + 120000; // 2 minutes
        let errorShown = false;
        while (Date.now() < deadline) {
            await delay(5000);
            // Stop once the payment is resolved by the webhook or cancelled.
            if (!this.paymentLineResolvers[paymentLine.uuid]) {
                return;
            }
            let data;
            try {
                data = await this.env.services.orm.silent.call(
                    "pos.payment.method",
                    "worldline_get_transaction_status",
                    [[paymentLine.payment_method_id.id], exchangeId]
                );
            } catch {
                continue;
            }
            if (!this.paymentLineResolvers[paymentLine.uuid]) {
                return;
            }
            if (data.status !== "done") {
                // Show a request error (e.g. terminal unreachable) once, but keep polling:
                // the transaction may still complete on the terminal.
                if (data.error && !errorShown) {
                    errorShown = true;
                    this._showWorldlineError(data.error);
                }
                continue;
            }
            this.handleWorldlineStatusResponse(paymentLine, data);
            return;
        }
    }

    handleWorldlineStatusResponse(paymentLine, payload) {
        paymentLine.transaction_id = payload.transaction_id;
        const cancelResolver = this._popCancelResolver(paymentLine);
        // Transaction successful
        if (payload.success) {
            paymentLine.card_brand = payload.card_brand;
            paymentLine.card_no = payload.card_no;
            paymentLine.payment_method_authcode = payload.payment_method_authcode;
        } else if (!cancelResolver) {
            // Transaction failed
            this._showWorldlineError(
                payload.error ?? _t("The transaction was declined or failed. Please try again.")
            );
        }
        cancelResolver?.(true);

        const resolver = this._popPaymentResolver(paymentLine);
        if (resolver) {
            resolver(payload.success);
        } else {
            paymentLine.handlePaymentResponse(payload.success);
        }
    }

    _extractErrorMessage(error) {
        if (typeof error === "string") {
            return error;
        }
        if (error.name === "RPC_ERROR") {
            return error.data.message;
        }
        return error.message;
    }

    _showWorldlineError(error) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("Worldline Error"),
            body: this._extractErrorMessage(error),
        });
    }
}

register_payment_method("worldline_api", PaymentWorldline);
