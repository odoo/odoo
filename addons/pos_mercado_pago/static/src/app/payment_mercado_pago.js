/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class PaymentMercadoPago extends PaymentInterface {
    async create_payment_intent() {
        const order = this.pos.get_order();
        const line = order.selected_paymentline;
        // Build informations for creating a payment intend on Mercado Pago.
        // Data in "external_reference" are send back with the webhook notification
        const infos = {
            amount: parseInt(line.amount * 100, 10),
            additional_info: {
                external_reference: `${this.pos.pos_session.id}_${line.payment_method.id}_${order.uid}`,
                print_on_terminal: true,
            },
        };
        // mp_payment_intent_create will call the Mercado Pago api
        return await this.env.services.orm.silent.call(
            "pos.payment.method",
            "mp_payment_intent_create",
            [[line.payment_method.id], infos]
        );
    }
    async get_last_status_payment_intent() {
        const line = this.pos.get_order().selected_paymentline;
        // mp_payment_intent_get will call the Mercado Pago api
        return await this.env.services.orm.silent.call(
            "pos.payment.method",
            "mp_payment_intent_get",
            [[line.payment_method.id], this.payment_intent.id]
        );
    }

    async cancel_payment_intent() {
        const line = this.pos.get_order().selected_paymentline;
        // mp_payment_intent_cancel will call the Mercado Pago api
        return await this.env.services.orm.silent.call(
            "pos.payment.method",
            "mp_payment_intent_cancel",
            [[line.payment_method.id], this.payment_intent.id]
        );
    }

    async get_payment(payment_id) {
        const line = this.pos.get_order().selected_paymentline;
        // mp_get_payment_status will call the Mercado Pago api
        return await this.env.services.orm.silent.call(
            "pos.payment.method",
            "mp_get_payment_status",
            [[line.payment_method.id], payment_id]
        );
    }

    setup() {
        super.setup(...arguments);
        this.webhook_resolver = null;
        this.payment_intent = {};
    }

    async send_payment_request(cid) {
        await super.send_payment_request(...arguments);
        const line = this.pos.get_order().selected_paymentline;
        try {
            // During payment creation, user can't cancel the payment intent
            line.set_payment_status("waitingCapture");
            // Call Mercado Pago to create a payment intent
            const payment_intent = await this.create_payment_intent();
            if (!("id" in payment_intent)) {
                this._showMsg(payment_intent.message, "error");
                return false;
            }
            // Payment intent creation successfull, save it
            this.payment_intent = payment_intent;
            // After payment creation, make the payment intent canceling possible
            line.set_payment_status("waitingCard");
            // Wait for payment intent status change and return status result
            return await new Promise((resolve) => {
                this.webhook_resolver = resolve;
            });
        } catch (error) {
            this._showMsg(error, "System error");
            return false;
        }
    }

    async send_payment_cancel(order, cid) {
        await super.send_payment_cancel(order, cid);
        if (!("id" in this.payment_intent)) {
            return true;
        }
        const canceling_status = await this.cancel_payment_intent();
        if ("error" in canceling_status) {
            const message =
                canceling_status.status === 409
                    ? _t("Payment has to be canceled on terminal")
                    : _t("Payment not found (canceled/finished on terminal)");
            this._showMsg(message, "info");
            return canceling_status.status !== 409;
        }
        return true;
    }

    async handleMercadoPagoWebhook() {
        const line = this.pos.get_order().selected_paymentline;
        const MAX_RETRY = 5; // Maximum number of retries for the "ON_TERMINAL" BUG
        const RETRY_DELAY = 1000; // Delay between retries in milliseconds for the "ON_TERMINAL" BUG

        const showMessageAndResolve = (messageKey, status, resolverValue) => {
            if (!resolverValue) {
                this._showMsg(messageKey, status);
            }
            line.set_payment_status("done");
            this.webhook_resolver?.(resolverValue);
            return resolverValue;
        };

        const handleFinishedPayment = async (paymentIntent) => {
            if (paymentIntent.state === "CANCELED") {
                return showMessageAndResolve(_t("Payment has been canceled"), "info", false);
            }
            if (["FINISHED", "PROCESSED"].includes(paymentIntent.state)) {
                const payment = await this.get_payment(paymentIntent.payment.id);
                if (payment.status === "approved") {
                    return showMessageAndResolve(_t("Payment has been processed"), "info", true);
                }
                return showMessageAndResolve(_t("Payment has been rejected"), "info", false);
            }
        }

        // No payment intent id means either that the user reload the page or
        // it is an old webhook -> trash
        if ("id" in this.payment_intent) {
            // Call Mercado Pago to get the payment intent status
            let last_status_payment_intent = await this.get_last_status_payment_intent();
            // Bad payment intent id, then it's an old webhook not related with the
            // current payment intent -> trash
            if (this.payment_intent.id == last_status_payment_intent.id) {
                if (["FINISHED", "PROCESSED", "CANCELED"].includes(last_status_payment_intent.state)) {
                    return await handleFinishedPayment(last_status_payment_intent);
                }
                // BUG Sometimes the Mercado Pago webhook return ON_TERMINAL
                // instead of CANCELED/FINISHED when we requested a payment status
                // that was actually canceled/finished by the user on the terminal.
                // Then the strategy here is to ask Mercado Pago MAX_RETRY times the
                // payment intent status, hoping going out of this status
                if (["OPEN", "ON_TERMINAL"].includes(last_status_payment_intent.state)) {
                    return await new Promise((resolve) => {
                        let retry_cnt = 0;
                        const s = setInterval(async () => {
                            last_status_payment_intent =
                                await this.get_last_status_payment_intent();
                            if (
                                ["FINISHED", "PROCESSED", "CANCELED"].includes(
                                    last_status_payment_intent.state
                                )
                            ) {
                                clearInterval(s);
                                resolve(await handleFinishedPayment(last_status_payment_intent));
                            }
                            retry_cnt += 1;
                            if (retry_cnt >= MAX_RETRY) {
                                clearInterval(s);
                                resolve(
                                    showMessageAndResolve(
                                        _t("Payment status could not be confirmed"),
                                        "error",
                                        false
                                    )
                                );
                            }
                        }, RETRY_DELAY);
                    });
                }
                // If the state does not match any of the expected values
                return showMessageAndResolve(_t("Unknown payment status"), "error", false);
            }
        }
    }

    // private methods
    _showMsg(msg, title) {
        this.env.services.popup.add(ErrorPopup, {
            title: "Mercado Pago " + title,
            body: msg,
        });
    }
}
