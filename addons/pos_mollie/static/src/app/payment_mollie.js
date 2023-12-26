/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class PaymentMollie extends PaymentInterface {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }

    /**
     * @override
     */
    send_payment_request(cid) {
        super.send_payment_request(cid);
        return this._make_mollie_payment(cid);
    }

    /**
     * @override
     *
     * At the moment, Mollie POS payments are no cancellable from the API call.
     * It can be only cancelled from the terminal itself. If you cancel the
     * transaction from the terminal, we get webhook call for status update and
     * `handleMollieStatusResponse` will handle cancellation.
     *
     * So we just guide user to cancel manually from terminal.
     */
    async send_payment_cancel(order, cid) {
        this.env.services.popup.add(ErrorPopup, {
            title: _t('Cancel payment'),
            body: _t('Mollie payments also need manual cancellation on the payment terminal.'),
        });
        super.send_payment_cancel(order, cid);
        return true;
    }

    /**
     * Call odoo backend to create payment request on mollie.
     */
    _make_mollie_payment(cid) {
        let order = this.pos.get_order();
        if (order.selected_paymentline.amount < 0) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        let payment_data = this._prepare_payment_data(cid);
        return this.env.services.orm.silent
            .call('pos.payment.method', 'mollie_payment_request', [
                [this.payment_method.id],
                payment_data
            ])
            .then((response_data) => {return this._mollie_handle_response(response_data);})
            .catch(this._handle_odoo_connection_failure.bind(this));
    }

    /**
     * Call odoo backend to create payment request on mollie.
     */
    _prepare_payment_data(cid) {
        const order = this.pos.get_order();
        const line = order.paymentlines.find((paymentLine) => paymentLine.cid === cid);
        return {
            'description': order.name,
            'pos_reference': order.uid,
            'currency': this.pos.currency.name,
            'amount': line.amount,
            'session_id': this.pos.pos_session.id,
            'order_type': 'pos'
        }
    }

    _handle_odoo_connection_failure(data = {}) {
        const line = this.get_pending_mollie_line();
        if (line) {
            line.set_payment_status("retry");
        }
        this._show_error(
            _t("Could not connect to the Odoo server, please check your internet connection and try again.")
        );
        return Promise.reject(data);
    }

    /**
     * This method handles the response that comes from Mollie
     * when we first make a request to pay.
     */
    _mollie_handle_response(response) {

        const line = this.get_pending_mollie_line();

        if (response.status != 'open') {
            this._show_error(response.detail);
            line.set_payment_status('retry');
            return Promise.resolve();
        }
        if (response.id) {
            line.transaction_id = response.id;
        }
        line.set_payment_status('waitingCard');
        return this.waitForPaymentConfirmation();

    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            this.paymentLineResolvers[this.get_pending_mollie_line().cid] = resolve;
        });
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Mollie is received via the webhook.
     */
    async handleMollieStatusResponse(response) {

        const line = this.get_pending_mollie_line();
        if (!response) {
            this._handle_odoo_connection_failure();
            return;
        }

        if (line.transaction_id != response.id) {
            return;
        }

        if (response.status == 'paid') {
            this._resolvePaymentStatus(true);
        } else if (['expired', 'canceled', 'failed'].includes(response.status)) {
            this._resolvePaymentStatus(false);
        }
    }

    _resolvePaymentStatus(state) {
        const line = this.get_pending_mollie_line();
        const resolver = this.paymentLineResolvers?.[line.cid];
        if (resolver) {
            resolver(state);
        } else {
            line.handle_payment_response(state);
        }
    }

    // --------------------
    // HELPER FUNCTIONS
    // --------------------

    get_pending_mollie_line() {
        return this.pos.getPendingPaymentLine("mollie");
    }

    _show_error(msg, title) {
        if (!title) {
            title = _t("Mollie Error");
        }
        this.env.services.popup.add(ErrorPopup, {
            title: title,
            body: msg,
        });
    }
}
