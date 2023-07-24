/** @odoo-module */

import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService } from "@web/core/utils/hooks";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";

export class Payment extends Component {
    static template = "pos_self_order.Payment";
    static components = { KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
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
            if (this.selfOrder.pos_payment_methods.length === 0) {
                const order = await this.rpc("/pos-self-order/process-new-order/kiosk", {
                    order: this.selfOrder.currentOrder,
                    access_token: this.selfOrder.access_token,
                    table_identifier: null,
                });
                this.selfOrder.updateOrderFromServer(order);
                this.router.navigate("payment_success");
            } else if (this.selfOrder.pos_payment_methods.length === 1) {
                this.selectMethod(this.selfOrder.pos_payment_methods[0].id);
            }
        });
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

    get showFooterBtn() {
        return this.selfOrder.paymentError || this.state.selection;
    }
}
