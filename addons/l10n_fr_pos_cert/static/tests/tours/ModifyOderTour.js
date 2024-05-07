/** @odoo-module */

import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ModifySavedUnpaidOrder", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("product_a", "1", "10"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            // Order will be in "saved" state
            TicketScreen.loadSelectedOrder(),
            {
                content: "click review button",
                trigger: ".btn-switchpane.review-button",
                mobile: true,
            },
            Order.hasLine({productName: "product_a"}),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.orderIsEmpty(),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("MergeLinesUnpaidOrder", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("product_a"),
            ProductScreen.clickDisplayedProduct("product_b"),
            ProductScreen.clickDisplayedProduct("product_a"),
            {
                content: "click review button",
                trigger: ".btn-switchpane.review-button",
                mobile: true,
            },
            // lines for product_a should be merged
            Order.hasLine({productName: "product_a", quantity: "2"}),
            Chrome.endTour(),
        ].flat(),
});
