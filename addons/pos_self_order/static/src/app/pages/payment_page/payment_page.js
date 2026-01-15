import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

// This component is only use in Kiosk mode
export class PaymentPage extends Component {
    static template = "pos_self_order.PaymentPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.selfOrder.isOrder();
        this.router = useService("router");
        this.state = useState({
            selection: true,
            paymentMethodId: null,
        });

        onMounted(() => {
            if (this.selfOrder.models["pos.payment.method"].length === 1) {
                this.selectMethod(this.selfOrder.models["pos.payment.method"].getFirst().id);
            }
        });

        onWillUnmount(() => {
            this.selfOrder.paymentError = false;
        });
    }

    back() {
        this.selfOrder.currentOrder.uiState.lineChanges = {};
        this.router.back();
    }

    selectMethod(methodId) {
        this.state.selection = false;
        this.state.paymentMethodId = methodId;
        this.startPayment();
    }

    get selectedPaymentMethod() {
        return this.selfOrder.models["pos.payment.method"].find(
            (p) => p.id === this.state.paymentMethodId
        );
    }

    // this function will be override by pos_online_payment_self_order module
    // in mobile is the only available payment method
    async startPayment() {
        this.selfOrder.paymentError = false;
        try {
            await rpc(`/kiosk/payment/${this.selfOrder.config.id}/kiosk`, {
                order: this.selfOrder.currentOrder.serializeForORM(),
                access_token: this.selfOrder.access_token,
                payment_method_id: this.state.paymentMethodId,
            });
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
        }
    }
}
