/** @odoo-module **/
/* global StripeTerminal */

export class StripeError extends Error {}

export class Stripe {
    constructor(...args) {
        this.setup(...args);
    }

    setup(
        env,
        stripePaymentMethod,
        access_token,
        pos_config_id,
        errorCallback,
        handleReaderConnection
    ) {
        this.env = env;
        this.terminal = null;
        this.access_token = access_token;
        this.stripePaymentMethod = stripePaymentMethod;
        this.pos_config_id = pos_config_id;
        this.errorCallback = errorCallback;
        this.handleReaderConnection = handleReaderConnection;

        this.createTerminal();
    }

    get connectionStatus() {
        return this.terminal.getConnectionStatus();
    }

    createTerminal() {
        this.terminal = StripeTerminal.create({
            onFetchConnectionToken: this.getBackendConnectionToken.bind(this),
            onConnectionStatusChange: this.handleReaderConnection.bind(this),
            onUnexpectedReaderDisconnect: () => {
                this.handleReaderConnection({
                    status: "not_connected",
                });
            },
        });
    }

    async startPayment(order) {
        try {
            const result = await this.env.services.rpc(
                `/kiosk/payment/${this.pos_config_id}/kiosk`,
                {
                    order: order,
                    access_token: this.access_token,
                    payment_method_id: this.stripePaymentMethod.id,
                }
            );
            const paymentStatus = result.payment_status;
            const savedOrder = result.order;
            await this.connectReader();
            const clientSecret = paymentStatus.client_secret;
            const paymentMethod = await this.collectPaymentMethod(clientSecret);
            const processPayment = await this.processPayment(paymentMethod.paymentIntent);
            await this.capturePayment(processPayment.paymentIntent.id, savedOrder);
        } catch (error) {
            this.errorCallback(error);
        }
    }

    async processPayment(paymentIntent) {
        const result = await this.terminal.processPayment(paymentIntent);

        if (result.error) {
            throw new StripeError(result.error.code);
        }

        return result;
    }

    async getBackendConnectionToken() {
        const data = await this.env.services.rpc("/pos-self-order/stripe-connection-token", {
            access_token: this.access_token,
            payment_method_id: this.stripePaymentMethod.id,
        });

        return data.secret;
    }

    async capturePayment(paymentIntentId, order) {
        return await this.env.services.rpc("/pos-self-order/stripe-capture-payment", {
            access_token: this.access_token,
            order_access_token: order.access_token,
            payment_intent_id: paymentIntentId,
            payment_method_id: this.stripePaymentMethod.id,
        });
    }

    async discoverReaders() {
        const result = await this.terminal.discoverReaders({
            allowCustomerCancel: true,
        });

        if (result.error) {
            throw new StripeError(result.error.code);
        }

        return result;
    }

    async connectReader() {
        if (this.connectionStatus !== "not_connected") {
            return;
        }

        const discoverReaders = await this.discoverReaders();
        const discoveredReaders = discoverReaders.discoveredReaders;
        const findLinkedReader = discoveredReaders.find(
            (reader) => reader.serial_number == this.stripePaymentMethod.stripe_serial_number
        );

        const result = await this.terminal.connectReader(findLinkedReader, {
            fail_if_in_use: true,
        });

        if (result.error) {
            throw new StripeError(result.error.code);
        }

        return result;
    }

    async collectPaymentMethod(clientSecret) {
        const result = await this.terminal.collectPaymentMethod(clientSecret);

        if (result.error) {
            throw new StripeError(result.error.code);
        }

        return result;
    }
}
