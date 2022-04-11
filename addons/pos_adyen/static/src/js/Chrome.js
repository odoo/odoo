/* @odoo-module */
'use strict';

import Chrome from 'point_of_sale.Chrome';
import Registries from 'point_of_sale.Registries';
import { onPosBroadcast } from 'point_of_sale.custom_hooks';

const PosAdyenChrome = Chrome => class PosAdyenChrome extends Chrome {
    setup() {
        super.setup(...arguments);
        onPosBroadcast('adyen-payment-status-received', this._onAdyenPaymentStatusReceived);
    }
    /**
     * When receiving payment status, we identify the order from the status and
     * find a pending payment. Then, validate the status with the pending payment.
     */
    _onAdyenPaymentStatusReceived([paymentMethodId, paymentStatus]) {
        const paymentMethod = this.env.pos.payment_methods.find(pm => pm.id == paymentMethodId);
        const order = paymentMethod.payment_terminal.identifyOrder(paymentStatus);

        if (!order) {
            // Order containing the pending payment might have been deleted.
            if (paymentStatus.latest_response.SaleToPOIResponse.PaymentResponse.Response.Result == 'Success') {
                // This means that a successful payment status was received for a deleted order.
                // I don't see how to reach this from the UI. In case it's reached, we show an error dialog.
                // One possibility is that the payment status took time to reach the server, and when the
                // notification is received, the corresponding order might have been deleted or it has been
                // synced to the server.
                // IMPROVEMENT: How about writing a message in the order in case it's in the database?
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Order not found'),
                    body: this.env._t(
                        'Order corresponding to the received payment notification might have been deleted.'
                    ),
                });
            }
            return;
        }

        const pendingPayment = order.get_paymentlines().find(payment => payment.payment_method.id == paymentMethod.id && !payment.is_done());

        if (!pendingPayment) {
            // I don't see how to reach this code.
            return;
        }

        if (paymentMethod.payment_terminal.hasWaitingPaymentRequest) {
            paymentMethod.payment_terminal.handleAsyncPaymentStatus(paymentStatus, order, pendingPayment);
        } else {
            const result = paymentMethod.payment_terminal.validatePaymentStatus(paymentStatus, order, pendingPayment);
            pendingPayment.setStatusAfterPaymentStatusValidation(result);
        }
    }
}

Registries.Component.extend(Chrome, PosAdyenChrome);

export default Chrome
