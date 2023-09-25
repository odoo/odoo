/** @odoo-module */
import { Component, whenReady, App, onMounted } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { Router } from "@pos_self_order/app/router";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { ComboPage } from "@pos_self_order/app/pages/combo_page/combo_page";
import { ProductPage } from "@pos_self_order/app/pages/product_page/product_page";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";
import { PaymentSuccessPage } from "@pos_self_order/app/pages/payment_success_page/payment_success_page";
import { EatingLocationPage } from "@pos_self_order/app/pages/eating_location_page/eating_location_page";
import { StandNumberPage } from "@pos_self_order/app/pages/stand_number_page/stand_number_page";
import { ClosedPage } from "@pos_self_order/app/pages/closed_page/closed_page";
import { OrdersHistoryPage } from "@pos_self_order/app/pages/order_history_page/order_history_page";

class selfOrderIndex extends Component {
    static template = "pos_self_order.selfOrderIndex";
    static props = [];
    static components = {
        Router,
        CartPage,
        ProductPage,
        ClosedPage,
        OrdersHistoryPage,
        ComboPage,
        PaymentPage,
        PaymentSuccessPage,
        ProductListPage,
        EatingLocationPage,
        StandNumberPage,
        LandingPage,
        MainComponentsContainer,
    };

    setup() {
        this.selfOrder = useSelfOrder();

        onMounted(() => {
            this.selfOrder.isSession();
        });
    }
}

export async function createPublicRoot() {
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    const app = new App(selfOrderIndex, {
        templates,
        env: env,
        dev: env.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    return app.mount(document.body);
}

createPublicRoot();
export default { selfOrderIndex, createPublicRoot };
