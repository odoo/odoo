/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_03_pos_with_lots", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.enterLotNumber("1"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1"),
            ProductScreen.pressNumpad("2"),
            ProductScreen.totalAmountIs("6.38"),
            ProductScreen.clickDisplayedProduct("Monitor Stand"),
            ProductScreen.enterLotNumber("2"),
            ProductScreen.pressNumpad("3"),
            ProductScreen.totalAmountIs("5"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.totalAmountIs("9.57"),
            ProductScreen.isShown(),
        ].flat(),
});
