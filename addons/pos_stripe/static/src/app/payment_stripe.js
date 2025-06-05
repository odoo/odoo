/* global StripeTerminal */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

export class PaymentStripe extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.createStripeTerminal();
    }

    stripeUnexpectedDisconnect() {
        // Include a way to attempt to reconnect to a reader ?
        this._showError(_t("Reader disconnected"));
    }

    async stripeFetchConnectionToken() {
        // Do not cache or hardcode the ConnectionToken.
        try {
            const data = await this.pos.data.silentCall(
                "pos.payment.method",
                "stripe_connection_token",
                []
            );
            if (data.error) {
                throw data.error;
            }
            return data.secret;
        } catch (error) {
            const { message } = error.data || error;
            this._showError(message, "Fetch Token");
            this.terminal = false;
        }
    }

    async discoverReaders() {
        const discoverResult = await this.terminal.discoverReaders({});
        if (discoverResult.error) {
            this._showError(_t("Failed to discover: %s", discoverResult.error));
        } else if (discoverResult.discoveredReaders.length === 0) {
            this._showError(_t("No available Stripe readers."));
        } else {
            // Need to stringify all Readers to avoid to put the array into a proxy Object not interpretable
            // for the Stripe SDK
            this.pos.discoveredReaders = JSON.stringify(discoverResult.discoveredReaders);
        }
    }

    async checkReader() {
        try {
            if (!this.terminal) {
                const createStripeTerminal = this.createStripeTerminal();
                if (!createStripeTerminal) {
                    throw _t("Failed to load resource: net::ERR_INTERNET_DISCONNECTED.");
                }
            }
        } catch (error) {
            console.error(error);
            this._showError(error);
            return false;
        }
        const line = this.pos.getOrder().getSelectedPaymentline();
        // Because the reader can only connect to one instance of the SDK at a time.
        // We need the disconnect this reader if we want to use another one
        if (
            this.pos.connectedReader != this.payment_method_id.stripe_serial_number &&
            this.terminal.getConnectionStatus() == "connected"
        ) {
            const disconnectResult = await this.terminal.disconnectReader();
            if (disconnectResult.error) {
                this._showError(disconnectResult.error.message, disconnectResult.error.code);
                line.setPaymentStatus("retry");
                return false;
            } else {
                return await this.connectReader();
            }
        } else if (this.terminal.getConnectionStatus() == "not_connected") {
            return await this.connectReader();
        } else {
            return true;
        }
    }

    async connectReader() {
        const line = this.pos.getOrder().getSelectedPaymentline();
        const discoveredReaders = JSON.parse(this.pos.discoveredReaders);
        for (const selectedReader of discoveredReaders) {
            if (selectedReader.serial_number == this.payment_method_id.stripe_serial_number) {
                try {
                    const connectResult = await this.terminal.connectReader(selectedReader, {
                        fail_if_in_use: true,
                    });
                    if (connectResult.error) {
                        throw connectResult;
                    }
                    this.pos.connectedReader = this.payment_method_id.stripe_serial_number;
                    return true;
                } catch (error) {
                    console.error(error);
                    if (error.error) {
                        this._showError(error.error.message, error.code);
                    } else {
                        this._showError(error);
                    }
                    line.setPaymentStatus("retry");
                    return false;
                }
            }
        }
        this._showError(
            _t(
                "Stripe readers %s not listed in your account",
                this.payment_method_id.stripe_serial_number
            )
        );
    }

    _getCapturedCardAndTransactionId(processPayment) {
        const charges = processPayment.paymentIntent.charges;
        if (!charges) {
            return [false, false];
        }

        const intentCharge = charges.data[0];
        const processPaymentDetails = intentCharge.payment_method_details;

        if (processPaymentDetails.type === "interac_present") {
            // Canadian interac payments should not be captured:
            // https://stripe.com/docs/terminal/payments/regional?integration-country=CA#create-a-paymentintent
            return ["interac", intentCharge.id];
        }
        const cardPresentBrand = this.getCardBrandFromPaymentMethodDetails(processPaymentDetails);
        if (cardPresentBrand.includes("eftpos")) {
            // Australian eftpos should not be captured:
            // https://stripe.com/docs/terminal/payments/regional?integration-country=AU
            return [cardPresentBrand, intentCharge.id];
        }

        return [false, false];
    }

    async collectPayment(amount) {
        const line = this.pos.getOrder().getSelectedPaymentline();
        const clientSecret = await this.fetchPaymentIntentClientSecret(
            line.payment_method_id,
            amount
        );
        if (!clientSecret) {
            line.setPaymentStatus("retry");
            return false;
        }
        line.setPaymentStatus("waitingCard");
        const collectPaymentMethod = await this.terminal.collectPaymentMethod(clientSecret);
        if (collectPaymentMethod.error) {
            this._showError(collectPaymentMethod.error.message, collectPaymentMethod.error.code);
            line.setPaymentStatus("retry");
            return false;
        } else {
            line.setPaymentStatus("waitingCapture");
            const processPayment = await this.terminal.processPayment(
                collectPaymentMethod.paymentIntent
            );
            line.transaction_id = collectPaymentMethod.paymentIntent.id;
            if (processPayment.error) {
                this._showError(processPayment.error.message, processPayment.error.code);
                line.setPaymentStatus("retry");
                return false;
            } else if (processPayment.paymentIntent) {
                line.setPaymentStatus("waitingCapture");

                const [captured_card_type, captured_transaction_id] =
                    this._getCapturedCardAndTransactionId(processPayment);
                if (captured_card_type && captured_transaction_id) {
                    line.card_type = captured_card_type;
                    line.transaction_id = captured_transaction_id;
                } else {
                    await this.captureAfterPayment(processPayment, line);
                }

                line.setPaymentStatus("done");
                return true;
            }
        }
    }

    createStripeTerminal() {
        try {
            this.terminal = StripeTerminal.create({
                onFetchConnectionToken: this.stripeFetchConnectionToken.bind(this),
                onUnexpectedReaderDisconnect: this.stripeUnexpectedDisconnect.bind(this),
            });
            this.discoverReaders();
            return true;
        } catch (error) {
            this._showError(_t("Failed to load resource: net::ERR_INTERNET_DISCONNECTED."), error);
            this.terminal = false;
            return false;
        }
    }

    getCardBrandFromPaymentMethodDetails(paymentMethodDetails) {
        // Both `card_present` and `interac_present` are "nullable" so we need to check for their existence, see:
        // https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-card_present
        // https://docs.stripe.com/api/charges/object#charge_object-payment_method_details-interac_present
        // In Canada `card_present` might not be present, but `interac_present` will be
        return (
            paymentMethodDetails?.card_present?.brand ||
            paymentMethodDetails?.interac_present?.brand ||
            ""
        );
    }

    async captureAfterPayment(processPayment, line) {
        // Don't capture if the customer can tip, in that case we
        // will capture later.
        if (!this.canBeAdjusted(line.uuid)) {
            const capturePayment = await this.capturePayment(processPayment.paymentIntent.id);
            if (capturePayment.charges) {
                line.card_type = this.getCardBrandFromPaymentMethodDetails(
                    capturePayment.charges.data[0].payment_method_details
                );
            }
            line.transaction_id = capturePayment.id;
        }
    }

    canBeAdjusted(uuid) {
        var order = this.pos.getOrder();
        var line = order.getPaymentlineByUuid(uuid);
        return (
            this.pos.config.set_tip_after_payment &&
            line.payment_method_id.use_payment_terminal === "stripe" &&
            line.card_type !== "interac" &&
            (!line.card_type || !line.card_type.includes("eftpos"))
        );
    }

    async capturePayment(paymentIntentId) {
        try {
            const data = await this.pos.data.silentCall(
                "pos.payment.method",
                "stripe_capture_payment",
                [paymentIntentId]
            );
            if (data.error) {
                throw data.error;
            }
            return data;
        } catch (error) {
            const { message } = error.data || error;
            this._showError(message, "Capture Payment");
            return false;
        }
    }

    async fetchPaymentIntentClientSecret(payment_method, amount) {
        try {
            const data = await this.pos.data.silentCall(
                "pos.payment.method",
                "stripe_payment_intent",
                [[payment_method.id], amount]
            );
            if (data.error) {
                throw data.error;
            }
            return data.client_secret;
        } catch (error) {
            const { message } = error.data || error;
            this._showError(message, "Fetch Secret");
            return false;
        }
    }

    async sendPaymentRequest(uuid) {
        /**
         * Override
         */
        await super.sendPaymentRequest(...arguments);
        const line = this.pos.getOrder().getSelectedPaymentline();
        line.setPaymentStatus("waiting");
        try {
            if (await this.checkReader()) {
                return await this.collectPayment(line.amount);
            }
        } catch (error) {
            console.error(error);
            this._showError(String(error));
            return false;
        }
    }

    async sendPaymentCancel(order, uuid) {
        /**
         * Override
         */
        super.sendPaymentCancel(...arguments);
        const line = this.pos.getOrder().getSelectedPaymentline();
        const stripeCancel = await this.stripeCancel();
        if (stripeCancel) {
            line.setPaymentStatus("retry");
            return true;
        }
    }

    async stripeCancel() {
        if (!this.terminal) {
            return true;
        } else if (this.terminal.getConnectionStatus() != "connected") {
            this._showError(_t("Payment cancelled because not reader connected"));
            return true;
        } else {
            const cancelCollectPaymentMethod = await this.terminal.cancelCollectPaymentMethod();
            if (cancelCollectPaymentMethod.error) {
                this._showError(
                    cancelCollectPaymentMethod.error.message,
                    cancelCollectPaymentMethod.error.code
                );
            }
            return true;
        }
    }

    // private methods

    _showError(msg, title) {
        if (!title) {
            title = _t("Stripe Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

register_payment_method("stripe", PaymentStripe);
