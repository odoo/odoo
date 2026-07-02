import { useState } from "@web/owl2/utils";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

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
            paymentCancelled: false,
            qrCode: null,
            fadeOut: false,
            paymentMethodType: null,
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

    async back() {
        if (this.state.paymentMethodType === "cash_machine" && !this.selfOrder.paymentError) {
            const paymentLine = this.selfOrder.getPendingPaymentLine(
                this.selectedPaymentMethod.payment_provider
            );
            if (paymentLine) {
                const cancelConfirmed = await ask(this.selfOrder.dialog, {
                    title: _t("Confirm cancellation"),
                    body: _t("Are you sure you want to cancel the cash machine payment?"),
                });
                if (!cancelConfirmed) {
                    return;
                }
                this.state.paymentCancelled = true;
                await this.selectedPaymentMethod.payment_interface.sendPaymentCancel(paymentLine);
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

    get selectedPaymentMethod() {
        return this.selfOrder.models["pos.payment.method"].find(
            (p) => p.id === this.state.paymentMethodId
        );
    }

    // this function will be override by pos_online_payment_self_order module
    // in mobile is the only available payment method
    async startPayment() {
        this.state.qrCode = null;
        this.state.paymentCancelled = false;
        this.selfOrder.paymentError = false;
        try {
            if (this.selectedPaymentMethod.payment_interface) {
                const result = this.selfOrder.currentOrder.addPaymentline(
                    this.selectedPaymentMethod
                );
                if (!result.status) {
                    throw new Error(`Adding payment line failed: ${result.data}`);
                }
                const newPaymentLine = result.data;
                try {
                    const paymentSuccessful = await newPaymentLine.pay();
                    if (
                        this.selectedPaymentMethod.payment_method_type === "cash_machine" &&
                        newPaymentLine.amount > this.selfOrder.currentOrder.totalDue
                    ) {
                        // This fixes payments from cash machines which give change
                        newPaymentLine.setAmount(this.selfOrder.currentOrder.totalDue);
                    }
                    if (!paymentSuccessful) {
                        if (newPaymentLine.useQr && newPaymentLine.qr_code) {
                            this.state.fadeOut = true;
                            setTimeout(() => {
                                this.state.qrCode = newPaymentLine.qr_code;
                                this.state.fadeOut = false;
                            }, 300);
                            return;
                        }

                        throw new Error("Payment failed");
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
            if (!this.state.paymentCancelled) {
                this.selfOrder.handleErrorNotification(error);
            }
            this.selfOrder.paymentError = true;
        }
    }

    get cashPaymentMethod() {
        if (this.selfOrder.config.self_ordering_mode === "kiosk") {
            return this.selfOrder.models["pos.payment.method"].find(
                (pm) => pm.is_cash_count && !pm.payment_provider
            );
        }
        return false;
    }
}
