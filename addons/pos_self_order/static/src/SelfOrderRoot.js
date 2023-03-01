/** @odoo-module */
import { Component, whenReady, App, useState, onWillStart, useSubEnv } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { setLoadXmlDefaultApp, templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { LandingPage } from "@pos_self_order/LandingPageComponents/LandingPage/LandingPage";
import { NavBar } from "@pos_self_order/NavBar/NavBar";
import { ProductMainView } from "@pos_self_order/ProductMainView/ProductMainView";
import { ProductList } from "@pos_self_order/ProductList/ProductList";
import { CartView } from "@pos_self_order/CartView/CartView";
import { OrderView } from "@pos_self_order/OrderView/OrderView";
import { OrdersList } from "@pos_self_order/OrdersList/OrdersList";
import { PaymentMethodsSelect } from "@pos_self_order/PaymentMethodsSelect/PaymentMethodsSelect";
import { HelpIcon } from "@pos_self_order/HelpIcon/HelpIcon";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { effect } from "@point_of_sale/utils";
/**
 * @typedef {import("@pos_self_order/jsDocTypes").Product} Product
 * @typedef {import("@pos_self_order/jsDocTypes").Order} Order
 * @typedef {import("@pos_self_order/jsDocTypes").CartItem} CartItem
 */
class SelfOrderRoot extends Component {
    /*
    This is the Root Component of the SelfOrder App
    Most of the business logic is done here
    The app has the folowing screens:
    0. LandingPage  -- the main screen of the app
            -- it has a button that redirects to the menu
            -- it shows the orders list
    1. ProductList -- the screen that shows the list of products ( the menu )
    2. ProductMainView  -- the screen that shows the details of a product ( the product page )
    3. CartView  -- the screen that shows the cart
    */
    setup() {
        /*
        In local storage we store the following information:
        - An object containing all the previous orders
            (we will json.stringify it and save it to local storage)
            for each order we save the following information:
                1. the order id
                2. access_token
                3. Order state ( draft, paid )
                4. Date
                5. Amount
                6. Order items 
        - The current order details: object containing the following information:
            1. order_id
            2. access_token
        - The current cart
        - The current table id
        - The current user name

        */
        this.selfOrder = useSelfOrder();
        /**
         * @type {{
         * currentScreen: number,
         * currentProduct: number,
         * cart: CartItem[],
         * currentOrderDetails: Object,
         * message_to_display: string,
         * user_name: string,
         * table_id: string,
         * order_to_pay: Order,
         * }}
         */
        this.state = useState({
            currentScreen: 0,
            currentProduct: 0,
            cart: JSON.parse(localStorage.getItem("cart")) ?? [],
            currentOrderDetails: JSON.parse(localStorage.getItem("currentOrderDetails")) ?? {},
            // this is a message that will be displayed to the user on the landing page
            // example: "Your order has been placed successfully", "Your order has been paid successfully"
            message_to_display: this.selfOrder.config.message_to_display ?? "",
            user_name: localStorage.getItem("user_name") ?? "",
            table_id: this.selfOrder.config.table_id ?? localStorage.getItem("table_id") ?? "",
            order_to_pay: {},
        });
        effect(
            (state) => {
                // it is possible to call the /pos-self-order route with the "message_to_display"
                // query param; the controller will put the value of this param in the "this.selfOrder.config.message_to_display"
                // variable; here we don't need this parameter anymore in the url so we remove it
                const url = new URL(location.href);
                url.searchParams.delete("message_to_display");
                window.history.replaceState({}, "", url.href);
                // we only want to display the message for 9 seconds
                setTimeout(() => {
                    state.message_to_display = "";
                }, "9000");
            },
            [this.state]
        );
        // Keep local storage in sync with state
        effect(
            (state) => {
                this.selfOrder.config.table_id = state.table_id;
                localStorage.setItem("table_id", state.table_id);
            },
            [this.state]
        );
        effect(
            (state) => {
                localStorage.setItem("user_name", state.user_name);
            },
            [this.state]
        );
        effect(
            (state) => {
                localStorage.setItem("cart", JSON.stringify(state.cart));
            },
            [this.state]
        );
        effect(
            (state) => {
                localStorage.setItem(
                    "currentOrderDetails",
                    JSON.stringify(state.currentOrderDetails)
                );
            },
            [this.state]
        );
        useSubEnv({ state: this.state });
        this.rpc = useService("rpc");
        onWillStart(async () => {
            this.result_from_get_menu = await this.rpc(`/pos-self-order/get-menu`, {
                pos_id: this.selfOrder.config.pos_id,
            });
            // we rename the "id" field to "product_id"
            // the product.product model uses "id",
            // but the pos.order.line model uses "product_id"
            // TODO: this productlList should be available to all the components
            // but there is no reason for it to be in the state, as it should never change
            // what is the best way to do this?
            /**
             * @type {Product[]}
             */
            console.log("this.result_from_get_menu :>> ", this.result_from_get_menu);
            this.productList = this.result_from_get_menu.map(
                ({ id, price_info, pos_categ_id, ...rest }) => ({
                    product_id: id,
                    // TODO: we have to TEST if prices are correctly displayed / calculated with tax included or tax excluded
                    list_price: this.selfOrder.config.show_prices_with_tax_included
                        ? price_info["price_with_tax"]
                        : price_info["price_without_tax"],
                    // We are using a system of tags to categorize products
                    // the categories of a product will also be considered as tags
                    // ex of tags: "Pizza", "Drinks", "Italian", "Vegetarian", "Vegan", "Gluten Free","healthy", "organic",
                    // "Spicy", "Hot", "Cold", "Alcoholic", "Non Alcoholic", "Dessert", "Breakfast", "Lunch", "Dinner"
                    // "pairs well with wine", "pairs well with beer", "pairs well with soda", "pairs well with water",
                    // "HAPPY HOUR", "kids menu",  "local", "seasonal"
                    tag_list: pos_categ_id ? new Set(pos_categ_id[1].split(" / ")) : new Set(),
                    ...rest,
                })
            );
            this.productList.forEach((product) => {
                if (
                    product.attribute_line_ids.some(
                        (id) => id in this.selfOrder.config.attributes_by_ptal_id
                    )
                ) {
                    product.attributes = _.map(
                        product.attribute_line_ids,
                        (id) => this.selfOrder.config.attributes_by_ptal_id[id]
                    ).filter((attr) => attr !== undefined);
                }
            });
            console.log("this.productList :>> ", this.productList);
        });
    }

    // TODO: refactor functions to regular functions instead of arrow functions
    viewLandingPage() {
        this.state.currentScreen = 0;
    }
    viewMenu() {
        this.state.currentScreen = 1;
    }
    viewProduct = (id) => {
        this.state.currentScreen = 2;
        this.state.currentProduct = id;
    };
    viewCart = () => {
        this.state.currentScreen = 3;
    };
    viewOrders = () => {
        this.state.currentScreen = 5;
    };
    payOrder = (order) => {
        this.state.order_to_pay = order;
        this.state.currentScreen = 4;
    };
    isProductInCart = (id, description) => {
        return (
            this.state.cart.find((item) => item.product_id === id) &&
            this.state.cart.find((item) => item.product_id === id).description === description
        );
    };
    /**
     * @param {number} id
     * @param {number} qty
     * @param {string} customer_note
     * @param {string} description
     */
    addToCart = (id, qty, customer_note, description, price_extra) => {
        // if the product is already in the cart we just increase the quantity
        if (this.isProductInCart(id, description)) {
            if (qty) {
                this.state.cart.find((item) => item.product_id === id).qty = qty;
            } else {
                this.removeProductFromCart(id, description);
            }
        }
        // if the product is not in the cart we add it to the cart
        else {
            if (qty) {
                this.state.cart.push({
                    product_id: id,
                    qty: qty,
                    customer_note: customer_note,
                    description: description,
                    price_extra: price_extra,
                });
            }
        }
        this.viewMenu();
    };

    removeProductFromCart = (id, description) => {
        this.state.cart = this.state.cart.filter(
            (item) => item.product_id !== id || item.description !== description
        );
    };
    getTotalCartQty = () => {
        return this.state.cart.reduce((sum, cartItem) => {
            return sum + cartItem.qty;
        }, 0);
    };
    // FIXME: i don't know if the price_extra is written with tax included or not
    getTotalCartCost = () => {
        return this.state.cart.reduce((sum, cartItem) => {
            return (
                sum +
                (this.productList.find((x) => x.product_id === cartItem.product_id).price_info
                    .price_with_tax +
                    cartItem.price_extra) *
                    cartItem.qty
            );
        }, 0);
    };
    getTotalTax = () => {
        return this.state.cart.reduce((sum, cartItem) => {
            const product_price = this.productList.find(
                (x) => x.product_id === cartItem.product_id
            ).price_info;
            return (
                sum +
                (product_price.price_with_tax - product_price.price_without_tax) * cartItem.qty
            );
        }, 0);
    };
    getOrdersListWithAddedOrder = (orders_list, order) => {
        const existing_order_index = orders_list.findIndex((x) => x.order_id === order.order_id);
        if (existing_order_index === -1) {
            return [].concat(order, orders_list);
        }
        orders_list[existing_order_index] = order;
        return orders_list;
    };
    sendOrder = async () => {
        try {
            /*
            If this is the first time the user is sending an order
            we just send the order items to the server
            If this is not the first time the user is sending an order
            ( the user is adding more items to an existing order )
            we send the order items along with the order id and access_token to the server
            */
            const order_context = {
                cart: this.state.cart,
                order_id: this.state.currentOrderDetails.order_id ?? null,
                access_token: this.state.currentOrderDetails.access_token ?? null,
            };
            this.posted_order = await this.rpc(
                `/pos-self-order/send-order/${this.selfOrder.config.pos_id}/${this.selfOrder.config.table_id}`,
                order_context
            );
            if (this.selfOrder.config.self_order_location === "table") {
                localStorage.setItem(
                    "orders_list",
                    JSON.stringify(
                        this.getOrdersListWithAddedOrder(
                            JSON.parse(localStorage.getItem("orders_list")) ?? [],
                            this.posted_order
                        )
                    )
                );
                // we want to keep the order id and access token  of the current order in the local storage
                // we will need them when the user wants to add more items to the order
                this.state.currentOrderDetails = (({ order_id, access_token }) => ({
                    order_id,
                    access_token,
                }))(this.posted_order);
            }
            this.state.message_to_display = "success";
            // we only want to clear the cart if the order was sent successfully
            // in the case of an unsuccessful order the user might want to try again
            this.state.cart = [];
        } catch (error) {
            console.error(error);
            this.state.message_to_display = "error";
        }
        if (this.selfOrder.config.self_order_location === "table") {
            this.state.message_to_display = "order_needs_payment";
            this.viewLandingPage();
        } else if (this.selfOrder.config.self_order_location === "kiosk") {
            this.payOrder(this.posted_order);
        }
    };
    //TODO QUESTION:
    // some of this functions i pass as props to the components that need them
    // why don't i export them from this file and import them in the components?

    static components = {
        LandingPage,
        ProductMainView,
        NavBar,
        ProductList,
        CartView,
        OrderView,
        OrdersList,
        HelpIcon,
        PaymentMethodsSelect,
    };
}
SelfOrderRoot.template = "SelfOrderRoot";
export async function createPublicRoot() {
    await whenReady();
    const wowlEnv = makeEnv();
    await startServices(wowlEnv);
    const app = new App(SelfOrderRoot, {
        templates,
        env: wowlEnv,
        dev: wowlEnv.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    setLoadXmlDefaultApp(app);
    return app.mount(document.body);
}
createPublicRoot();
export default { SelfOrderRoot, createPublicRoot };
