/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";
import { NavBar } from "@pos_self_order/components/navbar/navbar";
import { ProductCard } from "@pos_self_order/components/product_card/product_card";
import { Lines } from "@pos_self_order/components/lines/lines";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { PriceDetails } from "@pos_self_order/components/price_details/price_details";
import { _t } from "@web/core/l10n/translation";

export class OrderCart extends Component {
    static components = { NavBar, ProductCard, Lines, PriceDetails };
    static props = [];
    static template = "pos_self_order.OrderCart";
    setup() {
        this.selfOrder = useSelfOrder();
        this.sendInProgress = false;

        onWillStart(() => {
            this.selfOrder.getPricesFromServer();
        });
    }

    get buttonToShow() {
        return this.selfOrder.self_order_mode === "each" ? "Pay" : "Order";
    }

    async processOrder() {
        if (this.sendInProgress) {
            return;
        }

        if (this.selfOrder.self_order_mode === "meal") {
            this.sendInProgress = true;
            try {
                await this.selfOrder.sendDraftOrderToServer();
            } finally {
                this.sendInProgress = false;
            }
        } else {
            this.selfOrder.notification.add(_t("Not yet implemented!"), { type: "danger" });
        }
    }
}
