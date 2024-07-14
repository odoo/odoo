/** @odoo-module */

import { Component, whenReady, App } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { Orders } from "@pos_order_tracking_display/app/components/orders/orders";
import { OdooLogo } from "@point_of_sale/app/generic_components/odoo_logo/odoo_logo";
import { useOrderStatusDisplay } from "./order_tracking_display_service";
class OrderStatusDisplay extends Component {
    static components = { Orders, OdooLogo };
    setup() {
        this.orders = useOrderStatusDisplay();
    }
}
OrderStatusDisplay.template = "pos_order_tracking_display.OrderStatusDisplay";
export async function createPublicRoot() {
    await whenReady();
    const wowlEnv = makeEnv();
    await startServices(wowlEnv);
    const app = new App(OrderStatusDisplay, {
        templates,
        env: wowlEnv,
        dev: wowlEnv.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    return app.mount(document.body);
}
createPublicRoot();
export default { OrderStatusDisplay, createPublicRoot };
