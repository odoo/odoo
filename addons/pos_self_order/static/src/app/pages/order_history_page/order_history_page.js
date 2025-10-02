import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class OrdersHistoryPage extends Component {
    static template = "pos_self_order.OrdersHistoryPage";
    static props = {};

    async setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
    }

    get orders() {
        return this.selfOrder.models["pos.order"]
            .filter((o) => o.access_token)
            .sort((a, b) => b.id - a.id);
    }

    get lines() {
        return this.order.lines;
    }

    getPrice(line) {
        return line.displayPrice;
    }

    getOrderState(state) {
        return state === "draft" ? _t("Current") : state;
    }

    getNameAndDescription(line) {
        const fullName = line.full_product_name;
        const regex = /\(([^()]+)\)[^(]*$/;
        const matches = fullName.match(regex);

        if (matches && matches.length > 1) {
            const attributes = matches[matches.length - 1].trim();
            const productName = fullName.replace(matches[0], "").trim();
            return { productName, attributes };
        }

        return { productName: fullName, attributes: "" };
    }

    editOrder(order) {
        if (order.state === "draft") {
            this.selfOrder.selectedOrderUuid = order.uuid;
            this.router.navigate("cart");
        }
    }

    back() {
        this.router.navigate("default");
    }
}
