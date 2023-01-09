/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { ProductConfigurator } from "@point_of_sale/../tests/tours/helpers/ProductConfiguratorTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

// signal to start generating steps
// when finished, steps can be taken from getSteps
startSteps();

ProductScreen.do.confirmOpeningPopup();
// Go by default to home category
ProductScreen.do.clickHomeCategory();

// Click on Configurable Chair product
ProductScreen.do.clickDisplayedProduct("Configurable Chair");
ProductConfigurator.check.isShown();

// Cancel configuration, not product should be in order
ProductConfigurator.do.cancelAttributes();
ProductScreen.check.orderIsEmpty();

// Click on Configurable Chair product
ProductScreen.do.clickDisplayedProduct("Configurable Chair");
ProductConfigurator.check.isShown();

// Pick Color
ProductConfigurator.do.pickColor("Red");

// Pick Radio
ProductConfigurator.do.pickSelect("Metal");

// Pick Select
ProductConfigurator.do.pickRadio("Other");

// Fill in custom attribute
ProductConfigurator.do.fillCustomAttribute("Custom Fabric");

// Confirm configuration
ProductConfigurator.do.confirmAttributes();

// Check that the product has been added to the order with correct attributes and price
ProductScreen.check.selectedOrderlineHas(
    "Configurable Chair (Red, Metal, Other: Custom Fabric)",
    "1.0",
    "11.0"
);

// Orderlines with the same attributes should be merged
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct("Configurable Chair");
ProductConfigurator.do.pickColor("Red");
ProductConfigurator.do.pickSelect("Metal");
ProductConfigurator.do.pickRadio("Other");
ProductConfigurator.do.fillCustomAttribute("Custom Fabric");
ProductConfigurator.do.confirmAttributes();
ProductScreen.check.selectedOrderlineHas(
    "Configurable Chair (Red, Metal, Other: Custom Fabric)",
    "2.0",
    "22.0"
);

// Orderlines with different attributes shouldn't be merged
ProductScreen.do.clickHomeCategory();
ProductScreen.do.clickDisplayedProduct("Configurable Chair");
ProductConfigurator.do.pickColor("Blue");
ProductConfigurator.do.pickSelect("Metal");
ProductConfigurator.do.pickRadio("Leather");
ProductConfigurator.do.confirmAttributes();
ProductScreen.check.selectedOrderlineHas(
    "Configurable Chair (Blue, Metal, Leather)",
    "1.0",
    "10.0"
);

Tour.register("ProductConfiguratorTour", { test: true, url: "/pos/ui" }, getSteps());
