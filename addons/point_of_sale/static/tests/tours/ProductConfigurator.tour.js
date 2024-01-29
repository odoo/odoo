/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as ProductConfigurator from "@point_of_sale/../tests/tours/helpers/ProductConfiguratorTourMethods";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";

registry.category("web_tour.tours").add("ProductConfiguratorTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            // Go by default to home category
            ProductScreen.clickHomeCategory(),

            // Click on Configurable Chair product
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.isShown(),

            // Cancel configuration, not product should be in order
            ProductConfigurator.cancelAttributes(),
            ProductScreen.orderIsEmpty(),

            // Click on Configurable Chair product
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.isShown(),

            // Pick Color
            ProductConfigurator.pickColor("Red"),

            // Pick Radio
            ProductConfigurator.pickSelect("Metal"),

            // Pick Select
            ProductConfigurator.pickRadio("Other"),

            // Fill in custom attribute
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),

            // Confirm configuration
            ProductConfigurator.confirmAttributes(),

            // Check that the product has been added to the order with correct attributes and price
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "1.0",
                "11.0"
            ),

            // Orderlines with the same attributes should be merged
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.pickColor("Red"),
            ProductConfigurator.pickSelect("Metal"),
            ProductConfigurator.pickRadio("Other"),
            ProductConfigurator.fillCustomAttribute("Custom Fabric"),
            ProductConfigurator.confirmAttributes(),
            inLeftSide(Order.hasLine({
                    withClass: ".selected",
                    productName: "Configurable Chair",
                    quantity: "2",
                    price: "22.0",
                    atts: {
                        "Color": "Red ($ 1.00)",
                        "Chair Legs": "Metal",
                        "Fabrics": "Other"
                    }
                })
            ),
            // Orderlines with different attributes shouldn't be merged
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Configurable Chair"),
            ProductConfigurator.pickColor("Blue"),
            ProductConfigurator.pickSelect("Metal"),
            ProductConfigurator.pickRadio("Leather"),
            ProductConfigurator.confirmAttributes(),
            ProductScreen.selectedOrderlineHas(
                "Configurable Chair",
                "1.0",
                "10.0"
            ),
            Chrome.endTour(),
        ].flat(),
});
