/** @odoo-module */
import { Component, whenReady, App } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { setLoadXmlDefaultApp, templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { LandingPage } from "@pos_self_order/pages/landing_page/landing_page";
import { NavBar } from "@pos_self_order/components/navbar/navbar";
import { ProductMainView } from "@pos_self_order/pages/product_main_view/product_main_view";
import { OrderCart } from "@pos_self_order/pages/order_cart/order_cart";
import { ProductList } from "@pos_self_order/pages/product_list/product_list";
import { OrdersHistory } from "@pos_self_order/pages/orders_history/orders_history";
import { Router } from "@pos_self_order/router";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useSelfOrder } from "./self_order_service";

class SelfOrderRoot extends Component {
    static template = "pos_self_order.SelfOrderRoot";
    static props = [];
    static components = {
        LandingPage,
        ProductMainView,
        NavBar,
        ProductList,
        Router,
        OrderCart,
        OrdersHistory,
        MainComponentsContainer,
    };
    /*
    This is the Root Component of the SelfOrder App
    The app has the following screens:
    0. LandingPage  -- the main screen of the app
                    -- it has a button that redirects to the menu
                    -- it has a button that redirects to the orders, if there are any

    1. ProductList -- the screen that shows the list of products ( the menu )
    2. ProductMainView  -- the screen that shows the details of a product ( the product page )
    3. OrderCart -- the screen that shows the cart
    4. OrdersHistory -- the screen that shows the list of orders
    */
    setup() {
        this.selfOrder = useSelfOrder();
    }
}

export async function createPublicRoot() {
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    const app = new App(SelfOrderRoot, {
        templates,
        env: env,
        dev: env.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    setLoadXmlDefaultApp(app);
    return app.mount(document.body);
}
createPublicRoot();
export default { SelfOrderRoot, createPublicRoot };
