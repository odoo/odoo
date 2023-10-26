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
            const payAfter = this.selfOrder.config.self_ordering_pay_after; // each, meal
            const order = this.selfOrder.currentOrder;

            if (paymentMethods.length === 1) {
                this.selectMethod(this.selfOrder.pos_payment_methods[0].id);
            } else if (paymentMethods.length === 0) {
                let screenMode = "pay";

                if (!order.isSavedOnServer) {
                    await this.selfOrder.sendDraftOrderToServer();
                    screenMode = payAfter === "meal" ? "order" : "pay";
                }

                this.router.navigate("confirmation", {
                    orderAccessToken: order.access_token,
                    screenMode: screenMode,
                });
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
