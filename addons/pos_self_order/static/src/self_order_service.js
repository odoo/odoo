/** @odoo-module */
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { formatMonetary } from "@web/views/fields/formatters";
import { _t } from "@web/core/l10n/translation";
import { groupBy } from "@web/core/utils/arrays";
import { effect } from "@web/core/utils/reactive";
import { Order } from "./models/order";
import { Product } from "./models/product";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc_service";

export class SelfOrder {
    constructor(...args) {
        this.setup(...args);
    }
    setup(env, rpc, notification, router) {
        Object.assign(this, {
            ...session.pos_self_order_data,
        });

        this.env = env;
        this.router = router;
        this.rpc = rpc;
        this.orders = [];
        this.tagList = new Set();
        this.editedOrder = null;
        this.productByIds = {};
        this.priceLoading = false;
        this.currentProduct = 0;
        this.lastEditedProductId = null;
        this.productsGroupedByTag = {};
        this.notification = notification;
        this.initData();

        if (this.self_order_mode !== "qr_code") {
            effect((state) => this.saveOrderToLocalStorage(state.orders), [this]);
        }

        if (!this.has_active_session && this.self_order_mode !== "qr_code") {
            this.closeNotification = this.notification.add(
                _t("The restaurant is closed. You can browse the menu, but ordering is disabled."),
                { type: "warning" }
            );
        }
    }

    initData() {
        this.products = this.products.map((p) => {
            const product = new Product(p, this);

            this.tagList.add(...product.tags);
            this.productByIds[product.id] = product;

            return product;
        });

        if (this.self_order_mode !== "qr_code") {
            const orders = JSON.parse(localStorage.getItem("orders")) ?? [];

            this.orders.push(
                ...orders.map((o) => {
                    o.lines = o.lines.filter((l) => this.productByIds[l.product_id]);
                    return new Order(o);
                })
            );
        }

        this.productsGroupedByTag = this._getProductsGroupedByTag(this.products);
    }
    _getProductsGroupedByTag(products) {
        const productsDuplicatedSuchThatEachHasOneTag = products.flatMap((product) =>
            product.tags.map((tag) => ({ ...product, tag }))
        );
        return groupBy(productsDuplicatedSuchThatEachHasOneTag, "tag");
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

        const existingOrder = this.orders.find(
            (o) => (this.self_order_mode === "each" && !o.access_token) || o.state === "draft"
        );

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

    formatMonetary(price) {
        return formatMonetary(price, { currencyId: this.currency_id });
    }

    async sendDraftOrderToServer() {
        try {
            let order = {};

            if (this.currentOrder.isAlreadySent) {
                order = await this.rpc(`/pos-self-order/update-existing-order`, {
                    order: this.currentOrder,
                });
            } else {
                order = await this.rpc(`/pos-self-order/process-new-order`, {
                    order: this.currentOrder,
                    table_access_token: this?.table?.access_token,
                });
            }

            this.editedOrder = Object.assign(this.editedOrder, order);
            this.editedOrder.computelastChangesSent();

            if (this.self_order_mode === "each") {
                this.editedOrder = null;
            }

            this.notification.add(_t("Your order has been placed!"), { type: "success" });
        } catch (error) {
            this.handleErrorNotification(error, [this.editedOrder.access_token]);
        } finally {
            this.router.navigate("default");
        }
    }

    async getOrdersFromServer() {
        const accessTokens = this.orders.map((order) => order.access_token);

        try {
            const orderChanges = {};
            const orders = await this.rpc(`/pos-self-order/get-orders/`, {
                access_tokens: accessTokens,
            });

            this.orders = this.orders.filter((order) => {
                orderChanges[order.access_token] = order.lastChangesSent;
                return !order.access_token;
            });

            this.orders.push(
                ...orders.map((o) => {
                    const newOrder = new Order({
                        ...o,
                        lastChangesSent: orderChanges[o.access_token],
                    });
                    return newOrder;
                })
            );

            this.editedOrder = null;
        } catch (error) {
            this.handleErrorNotification(
                error,
                this.orders.map((order) => order.access_token)
            );
        }
    }

    async getPricesFromServer() {
        this.priceLoading = true;

        try {
            const taxes = await this.rpc(`/pos-self-order/get-orders-taxes/`, {
                order: this.currentOrder,
                pos_config_id: this.pos_config_id,
            });

            for (const line of this.editedOrder.lines) {
                const lineTaxes = taxes.lines.find((ol) => ol.uuid === line.uuid);
                line.price_subtotal = lineTaxes.price_subtotal;
                line.price_subtotal_incl = lineTaxes.price_subtotal_incl;
            }

            this.editedOrder.amount_total = taxes.amount_total;
            this.editedOrder.amount_tax = taxes.amount_tax;
        } catch (error) {
            this.handleErrorNotification(error);
        }

        this.priceLoading = false;
    }

    handleErrorNotification(error, accessToken = []) {
        let message = _t("An error has occurred");

        if (error instanceof RPCError) {
            if (error.data.name === "werkzeug.exceptions.Unauthorized") {
                message = _t("You're not authorized to perform this action");
            } else if (error.data.name === "werkzeug.exceptions.NotFound") {
                message = _t("Orders wasn't found on the server");
            }
        } else if (error instanceof ConnectionLostError) {
            message = _t("Connection lost, please try again later");
        }

        this.notification.add(message, {
            type: "danger",
        });

        if (accessToken) {
            this.editedOrder = null;
            this.orders = this.orders.filter((o) => !accessToken.includes(o.access_token));
        }
    }
}

export const selfOrderService = {
    dependencies: ["rpc", "notification", "router"],
    async start(env, { rpc, notification, router }) {
        return new SelfOrder(env, rpc, notification, router);
    },
};

registry.category("services").add("self_order", selfOrderService);

export function useSelfOrder() {
    return useState(useService("self_order"));
}
