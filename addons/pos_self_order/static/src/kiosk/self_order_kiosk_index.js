/** @odoo-module */
import { Component, whenReady, App } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { setLoadXmlDefaultApp, templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { LandingPage } from "@pos_self_order/kiosk/pages/landing_page/landing_page";
import { EatingLocation } from "@pos_self_order/kiosk/pages/eating_location/eating_location";
import { Product } from "@pos_self_order/kiosk/pages/product/product";
import { ProductList } from "@pos_self_order/kiosk/pages/product_list/product_list";
import { OrderCart } from "@pos_self_order/kiosk/pages/order_cart/order_cart";
import { Closed } from "@pos_self_order/kiosk/pages/closed/closed";
import { Payment } from "@pos_self_order/kiosk/pages/payment/payment";
import { Combo } from "@pos_self_order/kiosk/pages/combo/combo";
import { PaymentSuccess } from "@pos_self_order/kiosk/pages/payment_success/payment_success";
import { StandNumber } from "@pos_self_order/kiosk/pages/stand_number/stand_number";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { Router } from "@pos_self_order/common/router";

class selfOrderIndex extends Component {
    static template = "pos_self_order.selfOrderIndex";
    static props = [];
    static components = {
        Payment,
        EatingLocation,
        ProductList,
        OrderCart,
        PaymentSuccess,
        Closed,
        Combo,
        StandNumber,
        Product,
        LandingPage,
        Router,
        MainComponentsContainer,
    };

    setup() {
        this.selfOrder = useselfOrder();
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
    setLoadXmlDefaultApp(app);
    return app.mount(document.body);
}
createPublicRoot();
export default { selfOrderIndex, createPublicRoot };
