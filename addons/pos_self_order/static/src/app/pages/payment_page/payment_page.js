/** @odoo-module */

import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";

// This component is only use in Kiosk mode
export class PaymentPage extends Component {
    static template = "pos_self_order.PaymentPage";

    setup() {
        this.selfOrder = useSelfOrder();
        this.selfOrder.isOrder();
        this.router = useService("router");
        this.rpc = useService("rpc");
        this.state = useState({
            selection: true,
            paymentMethodId: null,
        });

        onWillUnmount(() => {
            this.selfOrder.paymentError = false;
        });

        onWillStart(async () => {
            const paymentMethods = this.selfOrder.pos_payment_methods;

            if (paymentMethods.length === 1) {
                this.selectMethod(this.selfOrder.pos_payment_methods[0].id);
            }
        });
    }

    get showFooterBtn() {
        return this.selfOrder.paymentError || this.state.selection;
    }

    selectMethod(methodId) {
        this.state.selection = false;
        this.state.paymentMethodId = methodId;
        this.startPayment();
    }

    get selectedPaymentMethod() {
        return this.selfOrder.pos_payment_methods.find((p) => p.id === this.state.paymentMethodId);
    }

    // this function will be override by pos_online_payment_self_order module
    // in mobile is the only available payment method
    async startPayment() {
        this.selfOrder.paymentError = false;
        try {
            const result = await this.rpc(`/kiosk/payment/${this.selfOrder.pos_config_id}/kiosk`, {
                order: this.selfOrder.currentOrder,
                access_token: this.selfOrder.access_token,
                payment_method_id: this.state.paymentMethodId,
            });
            const order = result.order;
            this.selfOrder.updateOrderFromServer(order);
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
        }
    }
}
