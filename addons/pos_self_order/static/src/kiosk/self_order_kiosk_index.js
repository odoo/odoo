/** @odoo-module */
import { Component, whenReady, App } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { setLoadXmlDefaultApp, templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { LandingPage } from "@pos_self_order/kiosk/pages/landing_page/landing_page";
import { EatingLocation } from "@pos_self_order/kiosk/pages/eating_location/eating_location";
import { Product } from "@pos_self_order/kiosk/pages/product/product";
import { ProductList } from "@pos_self_order/kiosk/pages/product_list/product_list";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useSelfOrderKiosk } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { Router } from "@pos_self_order/common/router";

class SelfOrderKioskIndex extends Component {
    static template = "pos_self_order.SelfOrderKioskIndex";
    static props = [];
    static components = {
        EatingLocation,
        ProductList,
        Product,
        LandingPage,
        Router,
        MainComponentsContainer,
    };

    setup() {
        this.selfOrderKiosk = useSelfOrderKiosk();
    }
}

export async function createPublicRoot() {
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    const app = new App(SelfOrderKioskIndex, {
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
export default { SelfOrderKioskIndex, createPublicRoot };
