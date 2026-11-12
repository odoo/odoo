/* global StripeTerminal */

import { electronicPaymentRegistry, PaymentMethod } from "@pos_payment_method/payment_method";
import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class PaymentMethodStripe extends PaymentMethod {
    supportsRefunds() {
        return false;
    }

    supportsReversals() {
        return true;
    }

    pollingIntervalMs() {
        return 0;
    }

    constructor() {
        super(...arguments);
        this.stripe = null;
        this.connectedReader = null;
        this.currentPaymentState = null;
        this.stripeLoaded = Promise.withResolvers();
        this._loadStripeLibrary();
    }

    _onUnexpectedReaderDisconnect() {
        this.connectedReader = null;
    }

    async _onFetchConnectionToken() {
        const { secret } = await this._initPaymentMethod();
        return secret;
    }

    _handleStripeError(stripeResult) {
        if (stripeResult.error) {
            throw new Error(
                _t("Error received from Stripe: %(code)s\n\n%(message)s", stripeResult.error)
            );
        }
        return stripeResult;
    }

    async _loadStripeLibrary() {
        try {
            if (!window.StripeTerminal) {
                await loadJS("https://js.stripe.com/terminal/v1/");
            }
            this.stripe = StripeTerminal.create({
                onFetchConnectionToken: this._onFetchConnectionToken.bind(this),
                onUnexpectedReaderDisconnect: this._onUnexpectedReaderDisconnect.bind(this),
            });
            this.stripeLoaded.resolve();
        } catch {
            this.stripeLoaded.reject(
                _t(
                    "Failed to load the Stripe SDK. Stripe functionality is unavailable, please reload the page to try loading it again."
                )
            );
        }
    }

    /** @param {string} serialNumber */
    async _getReader(serialNumber) {
        const { discoveredReaders } = await this.stripe
            .discoverReaders({
                simulated: serialNumber === "SIMULATOR",
            })
            .then(this._handleStripeError);

        const reader = discoveredReaders.find((reader) => reader.serial_number === serialNumber);
        if (!reader) {
            throw new Error(
                _t("No Stripe terminal with serial number %s could be found.", serialNumber)
            );
        }

        return reader;
    }

    /** @param {string} serialNumber */
    async _connectToReader(serialNumber) {
        const reader = await this._getReader(serialNumber);
        await this.stripe
            .connectReader(reader, {
                fail_if_in_use: true,
            })
            .then(this._handleStripeError);
        this.connectedReader = reader;
    }

    async _disconnectReader() {
        await this.stripe.disconnectReader();
        this.connectedReader = null;
    }

    /** @param {string} clientSecret */
    async _collectPaymentMethod(clientSecret, allowTips) {
        const { paymentIntent } = await this.stripe
            .collectPaymentMethod(clientSecret, {
                config_override: {
                    enable_customer_cancellation: true,
                    skip_tipping: !allowTips,
                },
            })
            .then(this._handleStripeError);

        return paymentIntent;
    }

    async _cancelCollectPaymentMethod() {
        await this.stripe.cancelCollectPaymentMethod().then(this._handleStripeError);
    }

    async _processPayment(collectedPayment) {
        const { paymentIntent } = await this.stripe
            .processPayment(collectedPayment)
            .then(this._handleStripeError);

        return paymentIntent;
    }

    async _cancelProcessPayment() {
        await this.stripe.cancelProcessPayment().then(this._handleStripeError);
    }

    async _connectToReaderAndProcessPayment(paymentIntent) {
        try {
            await this._connectToReader(paymentIntent.terminal_serial_number);
            if (this.currentPaymentState === "cancelling") {
                return this._handlePaymentResponse({ ...paymentIntent, status: "failed" });
            }

            this.currentPaymentState = "collecting";
            const collectedPayment = await this._collectPaymentMethod(
                paymentIntent.client_secret,
                paymentIntent.allow_tips
            );
            console.log(collectedPayment);

            this.currentPaymentState = "processing";
            const processedPayment = await this._processPayment(collectedPayment);

            this.currentPaymentState = "verifying";
            const paymentResponse = await this.getTransactionStatus(processedPayment.id);
            return this._handlePaymentResponse(paymentResponse);
        } catch (error) {
            return this._handlePaymentResponse({
                ...paymentIntent,
                error: error.message,
                status: "failed",
            });
        } finally {
            if (this.connectedReader) {
                await this._disconnectReader();
            }
            this.currentPaymentState = null;
        }
    }

    async startPayment(_amount, _currencyId, _extraArgs, onPaymentComplete) {
        if (this.currentPaymentState !== null) {
            throw new Error(_t("Another Stripe transaction is already in progress."));
        }

        this.currentPaymentState = "connecting";
        const paymentIntent = await super.startPayment(...arguments);
        this._connectToReaderAndProcessPayment(paymentIntent, onPaymentComplete);
        return paymentIntent;
    }

    startListening(transactionId) {
        super.startListening(...arguments);
        if (!this.currentPaymentState) {
            this.getTransactionStatus(transactionId).then((paymentIntent) => {
                if (paymentIntent.status !== "pending") {
                    return this._handlePaymentResponse(paymentIntent);
                }
                if (paymentIntent.stripe_status === "requires_payment_method") {
                    this._connectToReaderAndProcessPayment(paymentIntent);
                } else {
                    return this._handlePaymentResponse({
                        ...paymentIntent,
                        status: "failed",
                        error: _t("Unable to resume Stripe payment."),
                    });
                }
            });
        }
    }

    async cancelTransaction(transactionId) {
        if (this.currentPaymentState === "connecting") {
            this.currentPaymentState = "cancelling";
        } else if (this.currentPaymentState === "collecting") {
            await this._cancelCollectPaymentMethod();
        } else if (this.currentPaymentState === "processing") {
            await this._cancelProcessPayment();
        } else if (this.currentPaymentState === "verifying") {
            throw new Error(_t("Cannot cancel Stripe payment as it is already processed."));
        }
        return { transaction_id: transactionId };
    }
}

electronicPaymentRegistry.add("stripe", PaymentMethodStripe);
