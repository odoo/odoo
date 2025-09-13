/** @odoo-module **/

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosRestaurantRewardStay", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            FloorScreen.clickTable("5"),

            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("1.98"),
            FloorScreen.backToFloor(),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("1.98"),
        ].flat()
})
