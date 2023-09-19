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
            const type = this.selfOrder.config.self_ordering_mode;
            const paymentMethods = this.selfOrder.pos_payment_methods.filter(
                (p) => !p.is_online_payment
            );

            if (paymentMethods.length === 0 && type === "kiosk") {
                try {
                    const order = await this.rpc("/pos-self-order/process-new-order/kiosk", {
                        order: this.selfOrder.currentOrder,
                        access_token: this.selfOrder.access_token,
                        table_identifier: null,
                    });

                    this.selfOrder.updateOrderFromServer(order);
                } catch (error) {
                    this.selfOrder.handleErrorNotification(error);
                }

                this.router.navigate("payment_success");
            } else if (paymentMethods.length === 1 && type === "kiosk") {
                this.selectMethod(this.selfOrder.pos_payment_methods[0].id);
            }
        });
    }

    get showFooterBtn() {
        return this.selfOrder.paymentError || this.state.selection;
    }

    get paymentMethods() {
        return this.selfOrder.pos_payment_methods.filter((p) => !p.is_online_payment);
    }

    selectMethod(methodId) {
        this.state.selection = false;
        this.state.paymentMethodId = methodId;
        this.startPayment();
    }

    async startPayment() {
        this.selfOrder.paymentError = false;
        try {
            const order = await this.rpc(`/kiosk/payment/${this.selfOrder.pos_config_id}/kiosk`, {
                order: this.selfOrder.currentOrder,
                access_token: this.selfOrder.access_token,
                payment_method_id: this.state.paymentMethodId,
            });
            this.selfOrder.updateOrderFromServer(order);
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
        }
    }
}
