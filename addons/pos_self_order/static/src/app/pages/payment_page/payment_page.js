import { Component, onMounted, onWillUnmount, proxy } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

// This component is only use in Kiosk mode
export class PaymentPage extends Component {
    static template = "pos_self_order.PaymentPage";

    setup() {
        this.selfOrder = useSelfOrder();
        this.selfOrder.isOrder();
        this.router = useService("router");
        this.state = proxy({
            selection: true,
            paymentMethodId: null,
            paymentCancelled: false,
            qrCode: null,
            transactionId: null,
            fadeOut: false,
            paymentMethodType: null,
        });

        onMounted(() => {
            if (this.canAutoSelectFirstMethod()) {
                this.selectMethod(this.selfOrder.models["pos.payment.method"].getFirst().id);
            }
        });

        onWillUnmount(() => {
            this.selfOrder.paymentError = false;
        });
    }

    canAutoSelectFirstMethod() {
        return this.selfOrder.models["pos.payment.method"].length === 1;
    }

    async back() {
        if (this.state.paymentMethodType === "cash_machine" && !this.selfOrder.paymentError) {
            const cancelConfirmed = await ask(this.selfOrder.dialog, {
                title: _t("Confirm cancellation"),
                body: _t("Are you sure you want to cancel the cash machine payment?"),
            });
            if (!cancelConfirmed) {
                return;
            }
            this.state.paymentCancelled = true;
            try {
                await this.selectedPaymentMethod.payment_interface.cancelTransaction(
                    this.state.transactionId
                );
            } catch (error) {
                this.selfOrder.handleErrorNotification(error);
            }
        }
        this.selfOrder.currentOrder.uiState.lineChanges = {};
        this.router.back();
    }

    get showQrCode() {
        return this.state.paymentMethodType === "external_qr" && this.state.qrCode;
    }

    selectMethod(methodId) {
        if (methodId === this.cashPaymentMethod?.id) {
            this.selfOrder.confirmationPage(
                "pay",
                this.selfOrder.config.self_ordering_mode,
                this.selfOrder.currentOrder.access_token
            );
            return;
        }
        this.state.selection = false;
        this.state.paymentMethodId = methodId;
        this.state.paymentMethodType = this.selectedPaymentMethod.payment_method_type;
        this.startPayment();
    }

    get paymentMethods() {
        return this.selfOrder.paymentMethods;
    }

    get selectedPaymentMethod() {
        return this.selfOrder.models["pos.payment.method"].find(
            (p) => p.id === this.state.paymentMethodId
        );
    }

    async processElectronicPayment() {
        const { promise, resolve, reject } = Promise.withResolvers();
        const order = this.selfOrder.currentOrder;
        const startPaymentResult = await this.selectedPaymentMethod.payment_interface.startPayment(
            order.amount_total,
            order.currency_id.id,
            {
                kiosk_order_id: order.id,
                kiosk_payment_method_id: this.state.paymentMethodId,
            },
            (result) => {
                if (result.status === "failed") {
                    reject(new Error(result.error));
                }
                resolve(result);
            }
        );
        this.state.transactionId = startPaymentResult.transaction_id;
        if (startPaymentResult.qr_code) {
            this.state.qrCode = startPaymentResult.qr_code;
        }
        return await promise;
    }

    // this function will be override by pos_online_payment_self_order module
    // in mobile is the only available payment method
    async startPayment() {
        this.state.qrCode = null;
        this.state.paymentCancelled = false;
        this.selfOrder.paymentError = false;
        const order = this.selfOrder.currentOrder;
        const paymentInteface = this.selectedPaymentMethod.payment_interface;

        try {
            if (paymentInteface) {
                const payment = await this.processElectronicPayment();
                if (!paymentInteface.supportsBackendConfirmation()) {
                    await rpc("/kiosk/payment/add_unsafe_payment", {
                        access_token: this.selfOrder.access_token,
                        electronic_payment_id: paymentInteface.id,
                        order_id: order.id,
                        payment_method_id: this.state.paymentMethodId,
                        order_access_token: order.access_token,
                        payment_result: payment,
                    });
                }
            } else {
                await rpc(`/kiosk/payment/${this.selfOrder.config.id}/kiosk`, {
                    order: order.serializeForORM(),
                    access_token: this.selfOrder.access_token,
                    payment_method_id: this.state.paymentMethodId,
                });
            }
        } catch (error) {
            if (!this.state.paymentCancelled) {
                this.selfOrder.handleErrorNotification(error);
            }
            this.selfOrder.paymentError = true;
        }
    }

    get cashPaymentMethod() {
        if (this.selfOrder.config.self_ordering_mode === "kiosk") {
            return this.selfOrder.models["pos.payment.method"].find(
                (pm) => pm.type === "cash" && !pm.payment_provider
            );
        }
        return false;
    }
}
