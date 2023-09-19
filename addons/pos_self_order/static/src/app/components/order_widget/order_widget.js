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
        const mode = this.selfOrder.config.self_ordering_pay_after;
        const type = this.selfOrder.config.self_ordering_mode;
        const isPaymentMethod = this.selfOrder.pos_payment_methods.find(
            (p) => !p.is_online_payment
        );

        if (!isPaymentMethod) {
            return {
                label: _t("Pay at cashier"),
                disabled: this.selfOrder.currentOrder.lines.length === 0,
            };
        }

        return {
            label: mode === "each" || type === "kiosk" ? _t("Pay") : _t("Order"),
            disabled: this.selfOrder.currentOrder.lines.length === 0,
        };
    }

    get lineNotSend() {
        const lineNotSend = this.selfOrder.currentOrder.hasNotAllLinesSent();
        return lineNotSend.reduce(
            (acc, line) => {
                const currentQty = line.qty;
                const lastChange = this.selfOrder.currentOrder.lastChangesSent[line.uuid];
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
