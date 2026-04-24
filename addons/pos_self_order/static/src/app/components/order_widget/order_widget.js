import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";

export class OrderWidget extends Component {
    static template = "pos_self_order.OrderWidget";
    static props = ["action", "removeTopClasses?"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
    }

    cancel() {
        if (this.selfOrder.config.self_ordering_mode === "kiosk") {
            this.dialog.add(CancelPopup, {
                title: _t("Cancel order"),
                confirm: () => {
                    this.selfOrder.cancelOrder();
                },
            });
        } else {
            this.selfOrder.cancelOrder();
        }
    }

    get buttonToShow() {
        const currentPage = this.router.activeSlot;
        const payAfter = this.selfOrder.config.self_ordering_pay_after;

        const isNoLine = this.selfOrder.currentOrder.lines.length === 0;
        const hasNotAllLinesSent = this.selfOrder.currentOrder.unsentLines;

        let label = "";
        let disabled = false;

        if (currentPage === "product_list") {
            label = _t("Checkout");
            disabled = isNoLine || hasNotAllLinesSent.length === 0;
        } else if (
            payAfter === "meal" &&
            Object.keys(this.selfOrder.currentOrder.changes).length > 0
        ) {
            label = _t("Order");
            disabled = isNoLine;
        } else {
            label = this.selfOrder.hasPaymentMethod()
                ? _t("Pay")
                : hasNotAllLinesSent.length
                ? _t("Order")
                : "";
        }

        return { label, disabled };
    }

    // TODO: remove in master
    get lineNotSend() {
        return this.selfOrder.orderLineNotSend;
    }

    shouldGoBack() {
        const order = this.selfOrder.currentOrder;
        return (
            Object.keys(order.changes).length === 0 ||
            this.router.activeSlot === "cart" ||
            order.lines.length === 0
        );
    }

    get leftButton() {
        const back = this.shouldGoBack();
        return {
            name: back ? _t("Back") : _t("Discard"),
            icon: back ? "oi oi-chevron-left btn-back" : "btn-close btn-cancel",
        };
    }

    onClickleftButton() {
        const currentPage = this.router.activeSlot;
        if (this.shouldGoBack()) {
            if (currentPage === "product_list") {
                const targetPage = this.selfOrder.hasPresets() ? "location" : "default";
                this.router.navigate(targetPage);
            } else if (currentPage === "cart" && this.selfOrder.currentOrder.unsentLines.length) {
                this.router.navigate("product_list");
            } else {
                this.router.back();
            }
            return;
        }

        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: () => {
                this.selfOrder.cancelOrder();
                this.router.navigate("default");
            },
        });
    }

    get presetBtnName() {
        const order = this.selfOrder.currentOrder;
        const payAfter = this.selfOrder.config?.self_ordering_pay_after;
        const orderChanges = Object.keys(order.uiState.lineChanges).length;
        if (
            this.selfOrder.hasPresets() &&
            this.router.activeSlot === "cart" &&
            order.unsentLines.length &&
            !(payAfter === "meal" && orderChanges) // No preset change after first order (pay-after-meal)
        ) {
            return order.preset_id?.name;
        }
        return null;
    }

    onClickPresetBtn() {
        this.router.navigate("location", {}, { redirectPage: this.router.activeSlot });
    }
}
