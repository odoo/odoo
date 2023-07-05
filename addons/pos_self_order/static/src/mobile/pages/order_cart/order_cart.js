/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";
import { NavBar } from "@pos_self_order/mobile/components/navbar/navbar";
import { ProductCard } from "@pos_self_order/mobile/components/product_card/product_card";
import { Lines } from "@pos_self_order/mobile/components/lines/lines";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_service";
import { PriceDetails } from "@pos_self_order/mobile/components/price_details/price_details";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class OrderCart extends Component {
    static components = { NavBar, ProductCard, Lines, PriceDetails };
    static props = [];
    static template = "pos_self_order.OrderCart";
    setup() {
        this.selfOrder = useSelfOrder();
        this.sendInProgress = false;
        this.router = useService("router");

        onWillStart(() => {
            this.selfOrder.getPricesFromServer();
        });
    }

    get orderToPay() {
        //FIXME: need adaptation with pos_self_online_payment
        return this.selfOrder.self_order_mode === "each" ? true : false;
    }

    async processOrder() {
        if (this.sendInProgress) {
            return;
        }

        if (this.selfOrder.self_order_mode === "meal") {
            this.sendInProgress = true;
            try {
                await this.selfOrder.sendDraftOrderToServer();
                this.router.navigate("default");
            } finally {
                this.sendInProgress = false;
            }
        } else {
            this.selfOrder.notification.add(_t("Not yet implemented!"), { type: "danger" });
        }
    }
}
