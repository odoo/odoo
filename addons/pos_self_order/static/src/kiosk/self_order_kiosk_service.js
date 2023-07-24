/** @odoo-module */
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { Order } from "@pos_self_order/common/models/order";
import { Product } from "@pos_self_order/common/models/product";

export class SelfOrderKiosk {
    constructor(...args) {
        this.ready = this.setup(...args).then(() => this);
    }

    async setup(env, rpc, notification, router) {
        Object.assign(this, {
            ...session.pos_self_order_data,
        });

        this.env = env;
        this.router = router;
        this.rpc = rpc;
        this.orders = [];
        this.editedOrder = null;
        this.productByIds = {};
        this.priceLoading = false;
        this.currentProduct = 0;
        this.lastEditedProductId = null;
        this.productsGroupedByCategory = {};
        this.notification = notification;
        this.initData();
        this.categoryList = new Set(
            this.pos_category
                .sort((a, b) => a.sequence - b.sequence)
                .map((c) => c.name)
                .filter((c) => this.productsGroupedByCategory[c])
        );

        this.eatingLocation = null;
    }

    initData() {
        this.products = this.products.map((p) => {
            const product = new Product(p, this.show_prices_with_tax_included);
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

        this.productsGroupedByCategory = this.products.reduce((acc, product) => {
            product.pos_categ_ids.map((pos_categ_ids) => {
                acc[pos_categ_ids] = acc[pos_categ_ids] || [];
                acc[pos_categ_ids].push(product);
            });
            return acc;
        }, {});
    }
}

export const selfOrderKioskService = {
    dependencies: ["rpc", "notification"],
    async start(env, { rpc, notification }) {
        return new SelfOrderKiosk(env, rpc, notification).ready;
    },
};

registry.category("services").add("self_orçder_kiosk", selfOrderKioskService);

export function useSelfOrderKiosk() {
    return useState(useService("self_orçder_kiosk"));
}
