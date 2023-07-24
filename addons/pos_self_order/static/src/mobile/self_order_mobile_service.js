/** @odoo-module */
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { effect } from "@web/core/utils/reactive";
import { Order } from "@pos_self_order/common/models/order";
import { batched } from "@web/core/utils/timing";
import { selfOrderCommon } from "@pos_self_order/common/self_order_service";

export class SelfOrder extends selfOrderCommon {
    constructor(...args) {
        super();
        this.ready = this.setup(...args).then(() => this);
    }

    async setup(...args) {
        this.orders = [];
        this.editedOrder = null;
        this.ordering = false;

        await super.setup(...args);

        if (this.self_order_mode !== "qr_code") {
            effect((state) => this.saveOrderToLocalStorage(state.orders), [this]);
        }

        if (this.has_active_session && this.self_order_mode !== "qr_code" && this.access_token) {
            this.ordering = true;
        }

        if (this.self_order_mode !== "qr_code") {
            await this.getOrdersFromServer();
            effect(
                batched((state) => this.saveOrderToLocalStorage(state.orders)),
                [this]
            );
        }
    }

    initData() {
        super.initData();

        if (this.self_order_mode !== "qr_code") {
            const orders = JSON.parse(localStorage.getItem("orders")) ?? [];

            this.orders.push(
                ...orders.map((o) => {
                    o.lines = o.lines.filter((l) => this.productByIds[l.product_id]);
                    return new Order(o);
                })
            );
        }
    }

    saveOrderToLocalStorage(orders) {
        Array.isArray(orders) && localStorage.setItem("orders", JSON.stringify(orders));
    }

    // In case of self_order_mode === "meal", we keep the same order until the user pays
    // In case of self_order_mode === "each", we create a new order each time the user orders somethings
    get currentOrder() {
        if (this.editedOrder) {
            return this.editedOrder;
        }

        const existingOrder = this.orders.find((o) => o.state === "draft");

        if (!existingOrder) {
            const newOrder = new Order({
                pos_config_id: this.pos_config_id,
            });

            this.orders.push(newOrder);
            this.editedOrder = newOrder;
        } else {
            this.editedOrder = existingOrder;
        }

        return this.editedOrder;
    }

    cancelOrder() {
        const changes = this.currentOrder.lastChangesSent;
        const lines = this.currentOrder.lines;
        const keptLines = [];

        for (const line of lines) {
            const change = changes[line.uuid];

            if (change) {
                line.qty = change.qty;
                line.customer_note = change.customer_note;
                line.selected_attributes = change.selected_attributes;
                keptLines.push(line);
            }
        }

        this.currentOrder.lines = keptLines;

        if (this.currentOrder.totalQuantity === 0) {
            this.router.navigate("default");
        }
    }

    async sendDraftOrderToServer() {
        try {
            const rpcUrl = this.currentOrder.isAlreadySent
                ? "/pos-self-order/update-existing-order"
                : "/pos-self-order/process-new-order/self";

            const order = await this.rpc(rpcUrl, {
                order: this.currentOrder,
                access_token: this.access_token,
                table_identifier: this.table ? this.table.identifier : null,
            });

            this.editedOrder.access_token = order.access_token;
            this.updateOrdersFromServer([order], [order.access_token]);
            this.editedOrder.updateLastChanges();

            if (this.self_order_mode === "each") {
                this.editedOrder = null;
            }

            this.notification.add(_t("Your order has been placed!"), { type: "success" });

            return order;
        } catch (error) {
            this.handleErrorNotification(error, [this.editedOrder.access_token]);
            return false;
        }
    }

    async getOrdersFromServer() {
        const accessTokens = this.orders.map((order) => order.access_token).filter(Boolean);

        if (accessTokens.length === 0) {
            return;
        }

        try {
            const orders = await this.rpc(`/pos-self-order/get-orders/`, {
                access_token: this.access_token,
                order_access_tokens: accessTokens,
            });

            this.updateOrdersFromServer(orders, accessTokens);
            this.editedOrder = null;
        } catch (error) {
            this.handleErrorNotification(
                error,
                this.orders.map((order) => order.access_token)
            );
        }
    }

    updateOrdersFromServer(orders, localAccessToken) {
        //FIXME, if the user refresh the page with not sent, we will lost this data.
        const accessTokensFromServer = orders.map((order) => order.access_token);

        for (const order of this.orders) {
            if (order.access_token) {
                const orderFromServer = orders.find((o) => o.access_token === order.access_token);
                if (orderFromServer) {
                    order.updateDataFromServer(orderFromServer);
                }
            }
        }

        for (const index in this.orders) {
            if (
                !accessTokensFromServer.includes(this.orders[index].access_token) &&
                localAccessToken.includes(this.orders[index].access_token)
            ) {
                this.orders.splice(index, 1);
            }
        }
    }

    changeOrderState(access_token, state) {
        const order = this.orders.filter((o) => o.access_token === access_token);
        let message = _t("Your order status has been changed");

        if (order.length === 0) {
            throw new Error("Warning, no order with this access_token");
        } else if (order.length !== 1) {
            throw new Error("Warning, two orders with the same access_token");
        } else {
            order[0].state = state;
        }

        if (state === "paid") {
            this.editedOrder = null;
            message = _t("Your order has been paid");
        } else if (state === "cancel") {
            this.editedOrder = null;
            message = _t("Your order has been canceled");
        }

        this.notification.add(message, {
            type: "success",
        });
        this.router.navigate("default");
    }
}

export const selfOrderService = {
    dependencies: ["rpc", "notification", "router"],
    async start(env, { rpc, notification, router }) {
        return new SelfOrder(env, rpc, notification, router).ready;
    },
};

registry.category("services").add("self_order", selfOrderService);

export function useSelfOrder() {
    return useState(useService("self_order"));
}
