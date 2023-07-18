/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";

export class OnlinePaymentPopup extends AbstractAwaitablePopup {
    static template = "pos_online_payment.OnlinePaymentPopup";

    setup() {
        super.setup();
        if (this.props.order.uiState.PaymentScreen) {
            this.props.order.uiState.PaymentScreen.onlinePaymentPopup = this;
        }
    }
    setReceivedOrderServerOPData(opData) {
        this.opData = opData;
        this.confirm();
    }
    async confirm() {
        super.confirm();
        delete this.props.order.uiState.PaymentScreen?.onlinePaymentPopup;
    }
    cancel() {
        super.cancel();
        delete this.props.order.uiState.PaymentScreen?.onlinePaymentPopup;
    }
    async getPayload() {
        return this.opData;
    }
}
