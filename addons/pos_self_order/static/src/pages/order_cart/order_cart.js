/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { NavBar } from "@pos_self_order/components/navbar/navbar";
import { ProductCard } from "@pos_self_order/components/product_card/product_card";
import { Lines } from "@pos_self_order/components/lines/lines";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { PriceDetails } from "@pos_self_order/components/price_details/price_details";
import { PopupTable } from "@pos_self_order/components/popup_table/popup_table";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class OrderCart extends Component {
    static components = { NavBar, ProductCard, Lines, PriceDetails, PopupTable };
    static props = [];
    static template = "pos_self_order.OrderCart";
    setup() {
        this.selfOrder = useSelfOrder();
        this.sendInProgress = false;
        this.router = useService("router");
        this.state = useState({
            selectTable: false,
        });

        onWillStart(() => {
            this.selfOrder.getPricesFromServer();
        });
    }

    get buttonToShow() {
        return this.selfOrder.self_order_mode === "each" ? "Pay" : "Order";
    }

    async selectTable(table) {
        if (table) {
            this.selfOrder.table = table;
            this.router.addTableIdentifier(table);
            await this.processOrder();
        }
        this.state.selectTable = false;
    }

    async processOrder() {
        if (this.sendInProgress) {
            return;
        }

        if (!this.selfOrder.table) {
            this.state.selectTable = true;
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
