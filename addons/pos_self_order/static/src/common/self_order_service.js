/** @odoo-module */
import { Reactive } from "@web/core/utils/reactive";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";
import { Product } from "@pos_self_order/common/models/product";
import { session } from "@web/session";
import { getColor } from "@web/core/colors/colors";
import { categorySorter } from "@pos_self_order/common/utils";

export class selfOrderCommon extends Reactive {
    async setup(env, rpc, notification, router, bus_service, cookie) {
        // services
        this.env = env;
        this.router = router;
        this.rpc = rpc;
        this.notification = notification;
        this.bus_service = bus_service;
        this.cookie = cookie;

        // data
        Object.assign(this, {
            ...session.pos_self_order_data,
        });
        this.color = getColor(this.company_color);
        this.priceLoading = false;
        this.productByIds = {};
        this.productsGroupedByCategory = {};
        this.currentProduct = 0;
        this.lastEditedProductId = null;
        this.initData();
        this.categoryList = new Set(
            this.pos_category
                .sort((a, b) => a.sequence - b.sequence)
                .filter((c) => this.productsGroupedByCategory[c.name])
                .sort((a, b) => categorySorter(a, b, this.iface_start_categ_id))
        );
    }

    initData() {
        this.products = this.products.map((p) => {
            const product = new Product(p, this.show_prices_with_tax_included);
            this.productByIds[product.id] = product;
            return product;
        });

        this.productsGroupedByCategory = this.products.reduce((acc, product) => {
            product.pos_categ_ids.map((pos_categ_ids) => {
                acc[pos_categ_ids] = acc[pos_categ_ids] || [];
                acc[pos_categ_ids].push(product);
            });
            return acc;
        }, {});
    }

    async getPricesFromServer() {
        try {
            if (!this.currentOrder) {
                return;
            }

            this.priceLoading = true;
            const taxes = await this.rpc(`/pos-self-order/get-orders-taxes/`, {
                order: this.currentOrder,
                access_token: this.access_token,
            });

            this.currentOrder.updateDataFromServer(taxes);
        } catch (error) {
            this.handleErrorNotification(error);
        } finally {
            this.priceLoading = false;
        }
    }

    handleErrorNotification(error, accessToken = []) {
        let message = _t("An error has occurred");
        let cleanOrders = false;

        if (error instanceof RPCError) {
            if (error.data.name === "werkzeug.exceptions.Unauthorized") {
                message = _t("You're not authorized to perform this action");
                cleanOrders = true;
            } else if (error.data.name === "werkzeug.exceptions.NotFound") {
                message = _t("Orders not found on server");
                cleanOrders = true;
            }
        } else if (error instanceof ConnectionLostError) {
            message = _t("Connection lost, please try again later");
        }

        this.notification.add(message, {
            type: "danger",
        });

        if (accessToken && cleanOrders) {
            this.editedOrder = null;

            for (const index in this.orders) {
                if (accessToken.includes(this.orders[index].access_token)) {
                    this.orders.splice(index, 1);
                }
            }
        }
    }

    formatMonetary(price) {
        return formatMonetary(price, { currencyId: this.currency_id });
    }
}
