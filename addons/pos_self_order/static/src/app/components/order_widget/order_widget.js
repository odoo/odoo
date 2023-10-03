/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";

export class OrderWidget extends Component {
    static template = "pos_self_order.OrderWidget";
    static props = ["action"];

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
        const kioskPayment = this.selfOrder.pos_payment_methods.find((p) => !p.is_online_payment); // cannot be online payment in kiosk for instance
        const isLine = this.selfOrder.currentOrder.lines.length === 0;

        let label = "";
        let disabled = "";

        if (currentPage === "product_list") {
            label = _t("Order");
            disabled = isLine;
        } else if (payAfter === "meal" && !this.selfOrder.currentOrder.isSavedOnServer) {
            label = _t("Order");
            disabled = isLine || !kioskPayment;
        } else {
            label = kioskPayment ? _t("Pay") : _t("Pay at cashier");
            disabled = isLine || !kioskPayment;
        }

        return { label, disabled };
    }

    get lineNotSend() {
        const order = this.selfOrder.currentOrder;

        if (order.isSavedOnServer) {
            return {
                price: order.amount_total,
                count: order.totalQuantity,
            };
        }

        const lineNotSend = order.hasNotAllLinesSent();
        return lineNotSend.reduce(
            (acc, line) => {
                const currentQty = line.qty;
                const lastChange = order.lastChangesSent[line.uuid];
                const qty = !lastChange ? currentQty : currentQty - lastChange.qty;

                acc.count += qty;
                acc.price += line.displayPrice * qty;

                return acc;
            },
            {
                price: 0,
                count: 0,
            }
        );
    }
}
