/** @odoo-module */
import { Reactive, effect } from "@web/core/utils/reactive";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";
import { Product } from "@pos_self_order/app/models/product";
import { Combo } from "@pos_self_order/app/models/combo";
import { session } from "@web/session";
import { getColor } from "@web/core/colors/colors";
import { categorySorter, attributeFormatter } from "@pos_self_order/app/utils";
import { Order } from "@pos_self_order/app/models/order";
import { batched } from "@web/core/utils/timing";
import { useState, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";
import { formatDateTime } from "@web/core/l10n/dates";
import { printerService } from "@point_of_sale/app/printer/printer_service";
import { qrCodeSrc } from "@point_of_sale/utils";

export class SelfOrder extends Reactive {
    constructor(...args) {
        super();
        this.ready = this.setup(...args).then(() => this);
    }

    async setup(env, { rpc, notification, router, printer }) {
        // services
        this.notification = notification;
        this.router = router;
        this.env = env;
        this.rpc = rpc;
        this.printer = printer;

        // data
        Object.assign(this, {
            ...session.pos_self_order_data,
        });

        this.markupDescriptions();

        this.productsGroupedByCategory = {};
        this.lastEditedProductId = null;
        this.attributeValueById = {};
        this.currentProduct = 0;
        this.attributeById = {};
        this.priceLoading = false;
        this.rpcLoading = false;
        this.productByIds = {};
        this.paymentError = false;
        this.editedOrder = null;
        this.comboByIds = {};
        this.ordering = false;
        this.orders = [];
        this.color = getColor(this.company.color);

        this.initData();
        if (this.config.self_ordering_mode === "kiosk") {
            this.initKioskData();
        } else {
            await this.initMobileData();
        }
    }

    async confirmOrder() {
        const payAfter = this.config.self_ordering_pay_after; // each, meal
        const device = this.config.self_ordering_mode; // kiosk, mobile
        const service = this.config.self_ordering_service_mode; // table, counter
        const paymentMethods = this.pos_payment_methods; // Stripe, Adyen, Online
        const order = this.currentOrder;

        // Stand number page will recall this function after the stand number is set
        if (
            service === "table" &&
            !order.take_away &&
            device === "kiosk" &&
            !order.table_stand_number
        ) {
            this.router.navigate("stand_number");
            return;
        }

        // if the amount is 0, we don't need to go to the payment page
        // this directive works for both mode each and meal
        if (order.amount_total === 0 && order.lines.length > 0) {
            await this.sendDraftOrderToServer();
            this.router.navigate("confirmation", {
                orderAccessToken: order.access_token,
                screenMode: "order",
            });
            return;
        }

        // When no payment methods redirect to confirmation page
        // the client will be able to pay at counter
        if (paymentMethods.length === 0) {
            let screenMode = "pay";

            if (!order.isSavedOnServer) {
                await this.sendDraftOrderToServer();
                screenMode = payAfter === "meal" ? "order" : "pay";
            }

            this.router.navigate("confirmation", {
                orderAccessToken: order.access_token,
                screenMode: screenMode,
            });
        } else {
            // In meal mode, first time the customer validate his order, we send it to the server
            // and we redirect him to the confirmation page, the next time he validate his order
            // if the order is already saved on the server, we redirect him to the payment page
            // In each mode, we redirect the customer to the payment page directly
            if (payAfter === "meal" && !order.isSavedOnServer) {
                await this.sendDraftOrderToServer();
                this.router.navigate("confirmation", {
                    orderAccessToken: order.access_token,
                    screenMode: "order",
                });
            } else {
                this.router.navigate("payment");
            }
        }
    }

    get currentOrder() {
        if (this.editedOrder && this.editedOrder.state === "draft") {
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

    markupDescriptions() {
        for (const product of this.products) {
            product.description_self_order = product.description_self_order
                ? markup(product.description_self_order)
                : "";
        }
    }

    initData() {
        this.currentLanguage = this.config.self_ordering_available_language_ids.find(
            (l) => l.code === cookie.get("frontend_lang")
        );

        if (this.config.self_ordering_default_language_id && !this.currentLanguage) {
            this.currentLanguage = this.config.self_ordering_default_language_id;
        }

        cookie.set("frontend_lang", this.currentLanguage.code);

        this.products = this.products.map((p) => {
            const product = new Product(p, this.config.iface_tax_included);
            this.productByIds[product.id] = product;

            if (product.attributes.length > 0) {
                for (const atr of product.attributes) {
                    this.attributeById[atr.id] = atr;
                    for (const val of atr.values) {
                        val.attribute_id = atr.id;
                        this.attributeValueById[val.id] = val;
                    }
                }
            }

            return product;
        });

        this.combos = this.combos.map((c) => {
            const combo = new Combo(c);
            this.comboByIds[combo.id] = combo;
            return combo;
        });

        this.productsGroupedByCategory = this.products.reduce((acc, product) => {
            product.pos_categ_ids.map((categ) => {
                acc[categ.id] = acc[categ.id] || [];
                acc[categ.id].push(product);
            });
            return acc;
        }, {});

        if (this.productsGroupedByCategory[0]) {
            this.pos_category.push({
                has_image: false,
                id: 0,
                name: _t("Uncategorised"),
                sequence: 9999,
            });
        }

        this.categoryList = new Set(
            this.pos_category
                .sort((a, b) => a.sequence - b.sequence)
                .filter((c) => this.productsGroupedByCategory[c.id])
                .sort((a, b) => categorySorter(a, b, this.config.iface_start_categ_id))
        );

        this.currentCategory = this.pos_category.length > 0 ? [...this.categoryList][0] : null;
    }

    initKioskData() {
        if (this.pos_session && this.access_token) {
            this.ordering = true;
        }

        this.idleTimout = false;
        window.addEventListener("click", (event) => {
            this.idleTimout && clearTimeout(this.idleTimout);
            this.idleTimout = setTimeout(() => {
                if (this.router.activeSlot !== "payment") {
                    this.router.navigate("default");
                }
            }, 5 * 1000 * 60);
        });
    }

    async initMobileData() {
        if (this.config.self_ordering_mode !== "qr_code") {
            if (this.pos_session && this.access_token) {
                this.ordering = true;
            }

            if (!this.ordering) {
                return;
            }

            effect(
                batched((state) => this.saveOrderToLocalStorage(state.orders)),
                [this]
            );

            const orders = JSON.parse(localStorage.getItem("orders")) ?? [];
            this.orders.push(
                ...orders.map((o) => {
                    o.lines = o.lines.filter((l) => this.productByIds[l.product_id]);
                    return new Order(o);
                })
            );

            effect((state) => this.saveOrderToLocalStorage(state.orders), [this]);
            await this.getOrdersFromServer();
            await this.getPricesFromServer();
        }
    }

    saveOrderToLocalStorage(orders) {
        Array.isArray(orders) && localStorage.setItem("orders", JSON.stringify(orders));
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
                line.attribute_value_ids = change.attribute_value_ids;
                keptLines.push(line);
            }
        }

        this.currentOrder.lines = keptLines;

        if (this.currentOrder.totalQuantity === 0) {
            this.router.navigate("default");
            this.editedOrder = null;
            this.flushNotSentOrder();
        }
    }

    flushNotSentOrder() {
        this.orders = this.orders.filter((o) => o.isSavedOnServer);
    }

    async sendDraftOrderToServer() {
        if (this.currentOrder.isSavedOnServer || this.currentOrder.lines.length === 0) {
            return this.currentOrder;
        }

        try {
            const rpcUrl = this.currentOrder.isAlreadySent
                ? "/pos-self-order/update-existing-order"
                : `/pos-self-order/process-new-order/${this.config.self_ordering_mode}`;

            const order = await this.rpc(rpcUrl, {
                order: this.currentOrder,
                access_token: this.access_token,
                table_identifier: this.table ? this.table.identifier : null,
            });

            this.editedOrder.access_token = order.access_token;
            this.updateOrdersFromServer([order], [order.access_token]);
            this.editedOrder.updateLastChanges();

            if (this.config.self_ordering_pay_after === "each") {
                this.editedOrder = null;
            }

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

    updateOrdersFromServer(ordersFromServer, localAccessToken) {
        const accessTokensFromServer = ordersFromServer.map((order) => order.access_token);

        for (const order of this.orders) {
            if (order.access_token) {
                const orderFromServer = ordersFromServer.find(
                    (o) => o.access_token === order.access_token
                );
                if (orderFromServer) {
                    order.updateDataFromServer(orderFromServer);
                    const newLine = this.currentOrder.lines.find((l) => !l.id);
                    if (!newLine) {
                        order.updateLastChanges();
                    }
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
            this.handleErrorNotification(new Error("Warning, no order with this access_token"));
        } else if (order.length !== 1) {
            this.handleErrorNotification(
                new Error("Warning, two orders with the same access_token")
            );
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

    updateOrderFromServer(order) {
        this.currentOrder.updateDataFromServer(order);
    }

    isOrder() {
        if (!this.currentOrder || !this.currentOrder.lines.length) {
            this.router.navigate("default");
        }
    }

    async getPricesFromServer() {
        try {
            if (!this.currentOrder) {
                return;
            }
            if (this.priceLoading) {
                this.priceLoading.abort(false);
            }

            this.priceLoading = this.rpc(`/pos-self-order/get-orders-taxes/`, {
                order: this.currentOrder,
                access_token: this.access_token,
            });
            await this.priceLoading.then((taxes) => {
                this.currentOrder.updateDataFromServer(taxes);
                this.priceLoading = false;
            });
        } catch (error) {
            this.handleErrorNotification(error);
        }
    }

    handleErrorNotification(error, accessToken = []) {
        this.rpcLoading = false;

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

    handleProductChanges(payload) {
        const product = new Product(payload.product, this.config.iface_tax_included);
        this.productByIds[payload.product.id] = product;
        for (const categ of payload.product.pos_categ_ids) {
            if (!this.pos_category.map((c) => c.id).includes(categ.id)) {
                continue;
            }
            const index = this.productsGroupedByCategory[categ.id].findIndex(
                (p) => p.id === product.id
            );
            if (index >= 0) {
                this.productsGroupedByCategory[categ.id][index] = product;
            } else {
                this.productsGroupedByCategory[categ.id].push(product);
            }
        }
    }

    verifyCart() {
        let result = true;
        for (const line of this.currentOrder.hasNotAllLinesSent()) {
            if (line.combo_parent_uuid) {
                continue;
            }
            const alreadySent = this.currentOrder.lastChangesSent
                ? this.currentOrder.lastChangesSent[line.uuid]
                : false;
            const wrongChild = line.child_lines.find(
                (l) => !this.productByIds[l.product_id]?.self_order_available
            );
            if (wrongChild || !this.productByIds[line.product_id]?.self_order_available) {
                if (alreadySent) {
                    line.qty = alreadySent.qty;
                    line.customer_note = alreadySent.customer_note;
                    line.selected_attributes = alreadySent.selected_attributes;
                } else {
                    this.currentOrder.removeLine(line.uuid);
                }
                this.notification.add(
                    _t(
                        "%s is not available anymore, it has thus been removed from your order. Please review your order and validate it again.",
                        line.full_product_name
                    ),
                    { type: "danger" }
                );
                result = false;
            }
        }

        return result;
    }

    getProductDisplayPrice(product) {
        if (this.currentOrder.take_away) {
            return product.price_info.display_price_alternative;
        } else {
            return product.price_info.display_price_default;
        }
    }
    getLinePrice(line) {
        return this.config.iface_tax_included ? line.price_subtotal_incl : line.price_subtotal;
    }
    getSelectedAttributes(line) {
        const attributeValues = line.attribute_value_ids;
        const customAttr = line.custom_attribute_value_ids;
        return attributeFormatter(this.attributeById, attributeValues, customAttr);
    }
    getFullProductName(line) {
        const attrs = this.getSelectedAttributes(line);
        const attrsStr = " (" + attrs.map((a) => a.value).join(", ") + ")";
        return line.full_product_name + (attrs.length ? attrsStr : "");
    }
    getLineDisplayData(line) {
        return {
            productName: this.getFullProductName(line),
            price: this.formatMonetary(this.getLinePrice(line)),
            qty: line.qty.toString(),
            unitPrice: this.formatMonetary(this.getLinePrice(line) / line.qty),
            comboParent: line.combo_parent_uuid
                ? this.currentOrder.lines.find((l) => l.uuid === line.combo_parent_uuid)
                      .full_product_name
                : "",
            customerNote: line.customer_note,
        };
    }
    export_for_printing(order) {
        order.receiptDate ||= formatDateTime(luxon.DateTime.now());
        return {
            orderlines: order.lines.map(this.getLineDisplayData.bind(this)),
            amount_total: order.amount_total,
            amount_tax: order.amount_tax,
            total_without_tax: order.amount_total - order.amount_tax,
            total_paid: order.amount_paid,
            paymentlines: order.payment_lines,
            change: 0,
            tax_details: order.tax_details,
            name: order.pos_reference,
            date: order.receiptDate,
            ticket_code: this.company.point_of_sale_ticket_unique_code && order.ticketCode,
            base_url: this.base_url,
            footer: this.config.receipt_footer,
            headerData: {
                header: this.config.receipt_header,
                company: this.company,
                trackingNumber: order.trackingNumber,
                bigTrackingNumber: true,
                pickingService: this.config.self_ordering_service_mode,
                tableTracker: order.table_stand_number ?? false,
            },
            pos_qr_code:
                this.company.point_of_sale_use_ticket_qr_code &&
                qrCodeSrc(
                    `${this.base_url}/pos/ticket/validate?access_token=${order.access_token}`
                ),
        };
    }
}

export const selfOrderService = {
    dependencies: ["rpc", "notification", "router", "printer"],
    async start(env, { rpc, notification, router, printer }) {
        return new SelfOrder(env, { rpc, notification, router, printer }).ready;
    },
};

registry.category("services").add("printer", printerService);
registry.category("services").add("self_order", selfOrderService);

export function useSelfOrder() {
    return useState(useService("self_order"));
}
