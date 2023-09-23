/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { NavBar } from "@pos_self_order/mobile/components/navbar/navbar";
import { ProductCard } from "@pos_self_order/mobile/components/product_card/product_card";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_mobile_service";
import { PopupTable } from "@pos_self_order/mobile/components/popup_table/popup_table";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

export class OrderCart extends Component {
    static components = {
        NavBar,
        ProductCard,
        PopupTable,
        OrderWidget,
        Orderline,
    };
    static props = [];
    static template = "pos_self_order.OrderCart";
    setup() {
        this.selfOrder = useSelfOrder();
        this.sendInProgress = false;
        this.router = useService("router");
        this.state = useState({
            selectTable: false,
            cancelConfirmation: false,
        });

        onWillStart(() => {
            this.selfOrder.getPricesFromServer();
        });
    }

    get buttonToShow() {
        return {
            label: this.selfOrder.self_order_mode === "each" ? _t("Pay") : _t("Order"),
            disabled: false,
        };
    }

    get orderToPay() {
        return this.selfOrder.self_order_mode === "each";
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

    cancelToggle() {
        this.state.cancelConfirmation = !this.state.cancelConfirmation;
    }

    cancelOrder() {
        this.selfOrder.cancelOrder();
        this.cancelToggle();
    }
}
