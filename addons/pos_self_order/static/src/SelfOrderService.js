/** @odoo-module */
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { formatMonetary } from "@web/views/fields/formatters";
import { _t } from "@web/core/l10n/translation";
import { groupBy } from "@web/core/utils/arrays";
import { effect } from "@web/core/utils/reactive";

/**
 * @template T
 * @typedef {{ [k in keyof T]: T[k] } & {}} Prettify
 */

/**
 * @typedef {Object} ReducedOrder
 * @property {string} pos_reference
 * @property {string} access_token
 * @property {string} [state]
 *
 /**
 * @typedef {Prettify<ReducedOrder & {state: string, lines: OrderLine[], amount_total: number, amount_tax: number}>} Order
 */

/**
 * The type of orderline that we get from the Product Main View
 * It contains the keys necessary to uniqely identify an orderline
 * @typedef {Object} PreFormedOrderLine
 * @property {number} product_id
 * @property {string} customer_note
 * @property {string} description
 * @property {number} nonFinalQty
 * @property {price_extra} PriceInfo
 */

/**
 * The type of orderline that we send to the server
 * @typedef {Object} ReducedOrderLine
 * @property {number} product_id
 * @property {number} qty
 * @property {string} customer_note
 * @property {string} description
 */

/**
 * @typedef {Prettify<ReducedOrderLine & {price_extra: PriceInfo}>}  OrderLine
 */

/**
 * @typedef {Object} PriceInfo
 * @property {number} list_price
 * @property {number} price_with_tax
 * @property {number} price_without_tax
 */

/**
 * @typedef {Object} Product
 * @property {number} product_id
 * @property {PriceInfo} price_info
 * @property {string} tag
 * @property {string} name
 * @property {string} description_sale
 * @property {boolean} has_image
 * @property {Attribute[]} attributes
 */

/**
 * @typedef {Object} Attribute
 * @property {string} display_type - The type of display for the attribute.
 * @property {number} id - The unique identifier of the attribute.
 * @property {string} name - The name of the attribute.
 * @property {Value[]} values
 */

/**
 * @typedef {Object} Value - An array of objects representing the attribute values.
 * @property {bool | string} value.html_color - False if the value has no color, otherwise the color in hex format. ( ex: #FF0000 )
 * @property {number} value.id - The unique identifier of the value.
 * @property {boolean} value.is_custom
 * @property {string} value.name
 * @property {PriceInfo} value.price_extra
 */

export class SelfOrder {
    constructor(...args) {
        this.setup(...args);
    }
    setup(env, rpc, notification) {
        Object.assign(this, {
            env,
            rpc,
            notification,
            ...session.pos_self_order_data,
            // Global state
            currentProduct: 0,
            /** @type {OrderLine[]} */
            cart: JSON.parse(localStorage.getItem("cart")) ?? [],
            /** @type {ReducedOrder[] | Order[]} */
            orders: JSON.parse(localStorage.getItem("orders")) ?? [],
            currentlyEditedOrderLine: null,
        });

        // we create a set with all the tags that are present in the menu
        this.tagList = new Set(this.products.map((product) => product.tag));
        this.productsGroupedByTag = groupBy(this.products, "tag");
        // We want to keep a backup of some of the state in local storage
        effect(
            (state) => {
                Array.isArray(state.cart) &&
                    localStorage.setItem("cart", JSON.stringify(state.cart));
            },
            [this]
        );
        effect(
            (state) => {
                Array.isArray(state.orders) &&
                    localStorage.setItem("orders", JSON.stringify(state.orders));
            },
            [this]
        );
        if (!this.has_active_session) {
            this.closeNotification = this.notification.add(
                _t("The restaurant is closed. You can browse the menu, but ordering is disabled."),
                { type: "warning" }
            );
        }
    }

    /**
     * @param {OrderLine} orderLine
     */
    setCurrentlyEditedOrderLine(orderLine) {
        this.currentlyEditedOrderLine = orderLine;
    }

    /**
     * @param {number} price
     * @returns {number}
     */
    formatMonetary(price) {
        return formatMonetary(price, { currencyId: this.currency_id });
    }

    /**
     * @returns {number}
     */
    getTotalCartQty() {
        const cart = this.cart;
        return cart.reduce((sum, orderLine) => {
            return sum + orderLine.qty;
        }, 0);
    }

    /**
     * @returns {number}
     */
    getTotalCartCost() {
        const cart = this.cart;
        return cart.reduce((sum, orderLine) => {
            return (
                sum +
                (this.getProduct({ id: orderLine.product_id }).price_info.price_with_tax +
                    orderLine.price_extra.price_with_tax) *
                    orderLine.qty
            );
        }, 0);
    }

    /**
     * @returns {number}
     */
    getTotalCartTax() {
        return this._getTotalCartTax(this.cart);
    }
    /**
     * From the server, for each product we get both the price with and without tax.
     * We never actually compute taxes on the frontend.
     * Here we add up the tax for each product in the cart
     * @param {OrderLine[]} cart
     * @returns {number}
     */
    _getTotalCartTax(cart) {
        return cart.reduce((sum, orderLine) => {
            const product = this.getProduct({ id: orderLine.product_id });
            const getTax = (x) => x.price_with_tax - x.price_without_tax;
            return (
                sum + (getTax(product.price_info) + getTax(orderLine.price_extra)) * orderLine.qty
            );
        }, 0);
    }

    /**
     * @param {PreFormedOrderLine} preFormedOrderline
     */
    updateCart(preFormedOrderline) {
        const orderLineToReplace = this.currentlyEditedOrderLine;
        this.deleteOrderLine(orderLineToReplace);
        const orderLine = this.constructOrderline(preFormedOrderline);
        this.cart = this.getUpdatedCart(this.cart, orderLine);
    }

    deleteOrderLine(orderLine) {
        if (!orderLine) {
            return;
        }
        this.cart = this.cart.filter((x) => JSON.stringify(x) !== JSON.stringify(orderLine));
    }

    /**
     * Returns the cart with the updated item
     * if we are editing an orderline, instead of trying to change the existing orderline
     * we delete it and add a new one
     * @param {OrderLine[]} cart
     * @param {OrderLine} orderLine
     * @returns {OrderLine[]}
     */
    getUpdatedCart(cart, orderLine) {
        return cart
            .filter((item) => !this.canBeMerged(item, orderLine))
            .concat(orderLine.qty ? [orderLine] : []);
    }
    /**
     * @param {OrderLine} orderline1
     * @param {OrderLine} orderline2
     * @returns {boolean}
     */
    canBeMerged(orderline1, orderline2) {
        return (
            this.getProduct({ id: orderline1.product_id }).is_pos_groupable &&
            this.orderline_unique_keys.every((key) => orderline1[key] === orderline2[key])
        );
    }

    /**
     * @param {PreFormedOrderLine} preFormedOrderline
     * @returns {OrderLine?}
     */
    findMergeableOrderLine(preFormedOrderline) {
        return this.cart.find((item) => this.canBeMerged(item, preFormedOrderline));
    }

    /**
     * The selfOrder.updateCart method expects us to give it the
     * total qty the orderline should have.
     * If we are currently editing an existing orderline ( that means that we came to this
     * page from the cart page), it means that we are editing the total qty itself,
     * so we just return orderLine.qty.
     * If we came to this page from the products page, it means that we are adding items,
     * so we need to add the qty of the current product to the qty that is
     * already in the cart.
     * @param {PreFormedOrderLine} preFormedOrderline
     * @returns {number}
     */
    findOrderlineQty(preFormedOrderline) {
        // ordeline.qty can only be 0 if we are editing an existing orderline
        // If we are editing an existing orderline, we don't care about the
        // qty that might have already been in the cart.
        // This is why we only look at what quantity might already be in the cart
        // if orderline.qty != 0
        const qtyAlreadyInCart =
            preFormedOrderline.nonFinalQty &&
            (this.findMergeableOrderLine(preFormedOrderline)?.qty || 0);
        return qtyAlreadyInCart + preFormedOrderline.nonFinalQty;
    }
    /**
     * @param {PreFormedOrderLine}
     * @returns {OrderLine}
     */
    constructOrderline(preFormedOrderline) {
        const qty = this.findOrderlineQty(preFormedOrderline);
        return (({ nonFinalQty, ...rest }) => ({
            qty,
            ...rest,
        }))(preFormedOrderline);
    }

    /**
     * @param {Object} options
     * @param {number} options.id
     * @returns {Product}
     */
    getProduct({ id }) {
        return this.products.find((product) => product.product_id === id);
    }

    ////// Orders Logic /////////

    /**
     * @param {ReducedOrder[] |Order[]} orders
     * @param {ReducedOrder | Order} new_order
     * @returns {ReducedOrder[] | Order[]}
     */
    combineOrders(orders, new_order) {
        // We only want to keep the last 10 orders
        return [
            new_order,
            ...orders
                .filter((order) => order.pos_reference !== new_order.pos_reference)
                .slice(0, 9),
        ];
    }

    async sendOrder() {
        try {
            /*
            If this is the first time the user is sending an order
            we just send the order items to the server
            If this is not the first time the user is sending an order
            ( the user is adding more items to an existing order )
            we send the order items along with the order id and access_token to the server
            */
            /**@type {ReducedOrder} */
            const postedOrder = await this.rpc(`/pos-self-order/send-order`, this.getOrderData());
            this.orders = this.combineOrders(this.orders, postedOrder);
            this.notification.add(_t("Your order has been placed!"), { type: "success" });
            // we only want to clear the cart if the order was sent successfully;
            // in the case of an unsuccessful order the user might want to try again
            this.cart = [];
        } catch (error) {
            this.notification.add(_t("Error sending order"), { type: "danger" });
            console.error(error);
        } finally {
            this.navigate("/");
        }
    }
    /**
     * @returns {{pos_config_id: number, cart: ReducedOrderLine[], table_access_token: string, order_pos_reference: string, order_access_token: string}}}
     */
    getOrderData() {
        return {
            pos_config_id: this.pos_config_id,
            cart: this.extractCartData(this.cart),
            table_access_token: this?.table?.access_token,
            // The last order is always the first one in the array
            // The orders are kept in reverse chronological order
            order_pos_reference: this.orders?.[0]?.pos_reference,
            order_access_token: this.orders?.[0]?.access_token,
        };
    }
    /**
     * @param {OrderLine[]} cart
     * @returns {ReducedOrderLine[]}
     */
    extractCartData(cart) {
        return cart.map((orderLine) => ({
            product_id: orderLine.product_id,
            qty: orderLine.qty,
            description: orderLine.description,
            customer_note: orderLine.customer_note,
        }));
    }

    async updateOrders() {
        const old_orders = this.orders;
        // we set this to null so we have a way to see in the template
        // that we are still loading the orders
        this.orders = null;
        // This await is needed;
        this.orders = await this.getUpdatedOrdersFromServer(old_orders);
    }

    /**
     * @param {ReducedOrder[] | Order[]} old_orders_list
     * @returns {ReducedOrder[] | Order[]}
     */
    async getUpdatedOrdersFromServer(old_orders_list) {
        return await Promise.all(
            old_orders_list.map(async (order) =>
                order.state === "paid" || order.state === "done"
                    ? order
                    : this.getUpdatedOrderFromServer(order)
            )
        );
    }
    /**
     * @param {ReducedOrder | Order} old_orders_list
     * @returns {ReducedOrder | Order}
     */
    async getUpdatedOrderFromServer(order) {
        try {
            return await this.rpc(`/pos-self-order/view-order/`, {
                pos_reference: order.pos_reference,
                access_token: order.access_token,
            });
        } catch {
            return { ...order, state: "not found" };
        }
    }
}

export const selfOrderService = {
    dependencies: ["rpc", "notification"],
    async start(env, { rpc, notification }) {
        return new SelfOrder(env, rpc, notification);
    },
};
registry.category("services").add("self_order", selfOrderService);

export function useSelfOrder() {
    return useState(useService("self_order"));
}
