/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
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

    get cancelAvailable() {
        return (
            !this.selfOrder.currentOrder.isSavedOnServer ||
            this.selfOrder.config.self_ordering_mode === "kiosk"
        );
    }

    get buttonToShow() {
        const currentPage = this.router.activeSlot;
        const payAfter = this.selfOrder.config.self_ordering_pay_after;
        const kioskPayment = this.selfOrder.pos_payment_methods;
        const isNoLine = this.selfOrder.currentOrder.lines.length === 0;
        const hasNotAllLinesSent = this.selfOrder.currentOrder.hasNotAllLinesSent();
        const isMobilePayment = this.selfOrder.pos_payment_methods.find((p) => p.is_mobile_payment);

        let label = "";
        let disabled = false;

        if (currentPage === "product_list") {
            label = _t("Order");
            disabled = isNoLine || hasNotAllLinesSent.length == 0;
        } else if (payAfter === "meal" && !this.selfOrder.currentOrder.isSavedOnServer) {
            label = _t("Order");
            disabled = isNoLine;
        } else {
            label = kioskPayment ? _t("Pay") : _t("Order");
            disabled = !kioskPayment && !isMobilePayment;
        }

        if (this.selfOrder.currentOrder.amount_total === 0) {
            label = _t("Order");
        }

        return { label, disabled };
    }

    get lineNotSend() {
        const order = this.selfOrder.currentOrder;
        const lineNotSend = order.hasNotAllLinesSent();

        return lineNotSend.reduce(
            (acc, line) => {
                const currentQty = line.qty;
                const lastChange = order.lastChangesSent[line.uuid];
                const qty = !lastChange ? currentQty : currentQty - lastChange.qty;

                acc.count += qty;
                const subtotal = this.selfOrder.config.iface_tax_included
                    ? line.price_subtotal_incl
                    : line.price_subtotal;
                acc.price += (subtotal / currentQty) * qty;

                return acc;
            },
            {
                price: 0,
                count: 0,
            }
        );
    }

    get leftButton() {
        const order = this.selfOrder.currentOrder;
        const back =
            order.isSavedOnServer || this.router.activeSlot === "cart" || order.lines.length === 0;

        return {
            name: back ? _t("Back") : _t("Cancel"),
            icon: back ? "fa fa-arrow-left btn-back" : "btn-close btn-cancel",
        };
    }

    onClickleftButton() {
        const order = this.selfOrder.currentOrder;

        if (
            order.lines.length === 0 ||
            order.isSavedOnServer ||
            this.router.activeSlot === "cart"
        ) {
            this.router.back();
            return;
        } else {
            this.dialog.add(CancelPopup, {
                title: _t("Cancel order"),
                confirm: () => {
                    this.selfOrder.cancelOrder();
                    this.router.navigate("default");
                },
            });
        }
    }
}
