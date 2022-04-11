/* @odoo-module */

import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from 'point_of_sale.Registries';

const PosAdyenPaymentScreen = (PaymentScreen) => class PosAdyenPaymentScreen extends PaymentScreen {
    setup() {
        super.setup();
        owl.onMounted(this._onMounted);
    }
    /**
     * When opening payment screen, check if there is a pending payment.
     * If there is, check the latest status from the backend.
     * If the status corresponds to the currently selected order, try to
     * validate the pending payment with the payment status.
     */
    async _onMounted() {
        try {
            const pendingAdyenPayment = this.currentOrder
                .get_paymentlines()
                .find((payment) => payment.payment_method.use_payment_terminal == 'adyen' && !payment.is_done());

            if (pendingAdyenPayment) {
                const paymentTerminal = pendingAdyenPayment.payment_method.payment_terminal;
                const status = await this.pos.env.services.rpc({
                    model: 'pos.payment.method',
                    method: 'get_latest_adyen_status',
                    args: [[paymentTerminal.payment_method.id], paymentTerminal._adyen_get_sale_id()],
                });
                const order = paymentTerminal.identifyOrder(status);
                if (order && order.uid == this.currentOrder.uid) {
                    const result = paymentTerminal.validatePaymentStatus(status, this.currentOrder, pendingAdyenPayment);
                    pendingAdyenPayment.setStatusAfterPaymentStatusValidation(result);
                } else {
                    this.showNotification(this.env._t('Order corresponding to the payment status was not found.'));
                }
            }
        } catch (error) {
            console.error(error);
        }
    }
    /**
     * @override
     * Prevent sending payment request if there is a pending adyen payment from other order.
     */
    async _sendPaymentRequest({ detail: line }) {
        const paymentMethod = line.payment_method;
        if (paymentMethod.use_payment_terminal != 'adyen') {
            return super._sendPaymentRequest(...arguments);
        }

        // At this point, payment method is adyen.
        if (!paymentMethod.payment_terminal) {
            return;
        }

        if (paymentMethod.payment_terminal.hasWaitingPaymentRequest || this._hasOtherPendingPayment(paymentMethod)) {
            return this.showPopup('ErrorPopup', {
                title: this.env._t('Not allowed'),
                body: this.env._t('There is a pending payment request from other order.'),
            });
        }

        return super._sendPaymentRequest(...arguments);
    }

    _hasOtherPendingPayment(paymentMethod) {
        return (
            this.env.pos.orders
                .filter((order) => order.uid != this.currentOrder.uid)
                .reduce(
                    (payments, order) => [
                        ...payments,
                        ...order
                            .get_paymentlines()
                            .filter((payment) => payment.payment_method.id == paymentMethod.id && !payment.is_done()),
                    ],
                    []
                ).length > 0
        );
    }

};

Registries.Component.extend(PaymentScreen, PosAdyenPaymentScreen);
