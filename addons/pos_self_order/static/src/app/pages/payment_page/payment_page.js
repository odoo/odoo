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
            if (this.selectedPaymentMethod.payment_terminal) {
                const result = this.selfOrder.currentOrder.addPaymentline(
                    this.selectedPaymentMethod
                );
                if (!result.status) {
                    throw new Error(`Adding payment line failed: ${result.data}`);
                }
                const newPaymentLine = result.data;
                try {
                    const paymentSuccessful = await newPaymentLine.pay();
                    if (!paymentSuccessful) {
                        throw new Error("Payment terminal payment failed");
                    }
                } catch (err) {
                    this.selfOrder.currentOrder.removePaymentline(newPaymentLine);
                    throw err;
                }
            }
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
