/* @odoo-module */

import TicketScreen from 'point_of_sale.TicketScreen';
import Registries from 'point_of_sale.Registries';

const PosAdyenTicketScreen = (TicketScreen) => class PosAdyenTicketScreen extends TicketScreen {
    async _onBeforeDeleteOrder(order) {
        const pendingAdyenPayments = order.get_paymentlines().filter(payment => payment.payment_method.use_payment_terminal == 'adyen' && !payment.is_done());
        for (const pendingPayment of pendingAdyenPayments) {
            const paymentTerminal = pendingPayment.payment_method.payment_terminal;
            paymentTerminal.send_payment_cancel(order, pendingPayment.cid);
        }
        return super._onBeforeDeleteOrder(order);
    }
};

Registries.Component.extend(TicketScreen, PosAdyenTicketScreen);
