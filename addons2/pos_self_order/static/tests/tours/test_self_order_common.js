/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as Utils from "../helpers/utils";
import * as LandingPage from "../helpers/landing_page";
import * as ProductPage from "../helpers/product_page";

registry.category("web_tour.tours").add("self_order_is_close", {
    test: true,
    steps: () => [
        LandingPage.isClosed(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.checkIsNoBtn("Order"),
    ],
});
