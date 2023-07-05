/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { SelfOrderRouter } from "@pos_self_order/mobile/self_order_router_service";

patch(SelfOrderRouter.prototype, "pos_restaurant_self_order.SelfOrderRouter", {
    addTableIdentifier(table) {
        const url = new URL(browser.location.href);
        url.searchParams.append("table_identifier", table.identifier);
        history.replaceState({}, "", url);
    },
});
