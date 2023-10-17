/** @odoo-module */
/* global StripeTerminal */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

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
            const data = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "stripe_connection_token",
                []
            );
            if (data.error) {
                throw data.error;
            }
            return data.secret;
        } catch (error) {
            const message = error.code === 200 ? error.data.message : error.message;
            this._showError(message, 'Fetch Token');
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
            this._showError(error);
            return false;
        }
        const line = this.pos.get_order().selected_paymentline;
        // Because the reader can only connect to one instance of the SDK at a time.
        // We need the disconnect this reader if we want to use another one
        if (
            this.pos.connectedReader != this.payment_method.stripe_serial_number &&
            this.terminal.getConnectionStatus() == "connected"
        ) {
            const disconnectResult = await this.terminal.disconnectReader();
            if (disconnectResult.error) {
                this._showError(disconnectResult.error.message, disconnectResult.error.code);
                line.set_payment_status("retry");
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
        const line = this.pos.get_order().selected_paymentline;
        const discoveredReaders = JSON.parse(this.pos.discoveredReaders);
        for (const selectedReader of discoveredReaders) {
            if (selectedReader.serial_number == this.payment_method.stripe_serial_number) {
                try {
                    const connectResult = await this.terminal.connectReader(selectedReader, {
                        fail_if_in_use: true,
                    });
                    if (connectResult.error) {
                        throw connectResult;
                    }
                    this.pos.connectedReader = this.payment_method.stripe_serial_number;
                    return true;
                } catch (error) {
                    if (error.error) {
                        this._showError(error.error.message, error.code);
                    } else {
                        this._showError(error);
                    }
                    line.set_payment_status("retry");
                    return false;
                }
            }
        }
        this._showError(
            _t(
                "Stripe readers %s not listed in your account",
                this.payment_method.stripe_serial_number
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
        const cardPresentBrand = processPaymentDetails.card_present.brand;

        if (processPaymentDetails.type === "interac_present") {
            // Canadian interac payments should not be captured:
            // https://stripe.com/docs/terminal/payments/regional?integration-country=CA#create-a-paymentintent
            return ["interac", intentCharge.id];
        } else if (cardPresentBrand.includes("eftpos")) {
            // Australian eftpos should not be captured:
            // https://stripe.com/docs/terminal/payments/regional?integration-country=AU
            return [cardPresentBrand, intentCharge.id];
        }

        return [false, false];
    }

    async collectPayment(amount) {
        const line = this.pos.get_order().selected_paymentline;
        const clientSecret = await this.fetchPaymentIntentClientSecret(line.payment_method, amount);
        if (!clientSecret) {
            line.set_payment_status("retry");
            return false;
        }
        line.set_payment_status("waitingCard");
        const collectPaymentMethod = await this.terminal.collectPaymentMethod(clientSecret);
        if (collectPaymentMethod.error) {
            this._showError(collectPaymentMethod.error.message, collectPaymentMethod.error.code);
            line.set_payment_status("retry");
            return false;
        } else {
            line.set_payment_status("waitingCapture");
            const processPayment = await this.terminal.processPayment(
                collectPaymentMethod.paymentIntent
            );
            line.transaction_id = collectPaymentMethod.paymentIntent.id;
            if (processPayment.error) {
                this._showError(processPayment.error.message, processPayment.error.code);
                line.set_payment_status("retry");
                return false;
            } else if (processPayment.paymentIntent) {
                line.set_payment_status("waitingCapture");

                const [captured_card_type, captured_transaction_id] = this._getCapturedCardAndTransactionId(processPayment);
                if (captured_card_type && captured_transaction_id) {
                    line.card_type = captured_card_type;
                    line.transaction_id = captured_transaction_id;
                } else {
                    await this.captureAfterPayment(processPayment, line);
                }

                line.set_payment_status("done");
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

    async captureAfterPayment(processPayment, line) {
        const capturePayment = await this.capturePayment(processPayment.paymentIntent.id);
        if (capturePayment.charges) {
            line.card_type =
                capturePayment.charges.data[0].payment_method_details.card_present.brand;
        }
        line.transaction_id = capturePayment.id;
    }

    async capturePayment(paymentIntentId) {
        try {
            const data = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "stripe_capture_payment",
                [paymentIntentId]
            );
            if (data.error) {
                throw data.error;
            }
            return data;
        } catch (error) {
            const message = error.code === 200 ? error.data.message : error.message;
            this._showError(message, 'Capture Payment');
            return false;
        }
    }

    async fetchPaymentIntentClientSecret(payment_method, amount) {
        try {
            const data = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "stripe_payment_intent",
                [[payment_method.id], amount]
            );
            if (data.error) {
                throw data.error;
            }
            return data.client_secret;
        } catch (error) {
            const message = error.code === 200 ? error.data.message : error.message;
            this._showError(message, 'Fetch Secret');
            return false;
        }
    }

    async send_payment_request(cid) {
        /**
         * Override
         */
        await super.send_payment_request(...arguments);
        const line = this.pos.get_order().selected_paymentline;
        line.set_payment_status("waiting");
        try {
            if (await this.checkReader()) {
                return await this.collectPayment(line.amount);
            }
        } catch (error) {
            this._showError(error);
            return false;
        }
    }

    async send_payment_cancel(order, cid) {
        /**
         * Override
         */
        super.send_payment_cancel(...arguments);
        const line = this.pos.get_order().selected_paymentline;
        const stripeCancel = await this.stripeCancel();
        if (stripeCancel) {
            line.set_payment_status("retry");
            return true;
        }
    }

    async stripeCancel() {
        if (!this.terminal) {
            return true;
        } else if (this.terminal.getConnectionStatus() != "connected") {
            this._showError(_t("Payment canceled because not reader connected"));
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
        this.env.services.popup.add(ErrorPopup, {
            title: title,
            body: msg,
        });
    }
}
