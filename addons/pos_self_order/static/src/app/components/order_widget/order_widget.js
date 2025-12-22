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
            Object.keys(this.currentOrder.changes).length > 0 ||
            this.selfOrder.config.self_ordering_mode === "kiosk"
        );
    }

    get buttonToShow() {
        const currentPage = this.router.activeSlot;
        const payAfter = this.selfOrder.config.self_ordering_pay_after;
        const kioskPayment = this.selfOrder.models["pos.payment.method"].getAll();
        const isNoLine = this.selfOrder.currentOrder.lines.length === 0;
        const hasNotAllLinesSent = this.selfOrder.currentOrder.unsentLines;
        const isMobilePayment = kioskPayment.find((p) => p.is_mobile_payment);

        let label = "";
        let disabled = false;

        if (currentPage === "product_list") {
            label = _t("Order");
            disabled = isNoLine || hasNotAllLinesSent.length == 0;
        } else if (
            payAfter === "meal" &&
            Object.keys(this.selfOrder.currentOrder.changes).length > 0
        ) {
            label = _t("Order");
            disabled = isNoLine;
        } else {
            label = kioskPayment ? _t("Pay") : _t("Order");
            disabled = !kioskPayment && !isMobilePayment;
        }

        return { label, disabled };
    }

    get lineNotSend() {
        const changes = this.selfOrder.currentOrder.changes;
        return Object.entries(changes).reduce(
            (acc, [key, value]) => {
                if (value.qty && value.qty > 0) {
                    const line = this.selfOrder.models["pos.order.line"].getBy("uuid", key);
                    acc.count += value.qty;
                    acc.price += line.get_display_price();
                }
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
            Object.keys(order.changes).length === 0 ||
            this.router.activeSlot === "cart" ||
            order.lines.length === 0;

        return {
            name: back ? _t("Back") : _t("Cancel"),
            icon: back ? "fa fa-arrow-left btn-back" : "btn-close btn-cancel",
        };
    }

    onClickleftButton() {
        const order = this.selfOrder.currentOrder;

        if (
            order.lines.length === 0 ||
            Object.keys(order.changes).length === 0 ||
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
