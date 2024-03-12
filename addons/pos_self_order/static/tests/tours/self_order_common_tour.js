/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

registry.category("web_tour.tours").add("self_order_is_close", {
    test: true,
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
    ],
});
