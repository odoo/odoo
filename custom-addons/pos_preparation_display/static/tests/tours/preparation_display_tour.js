/** @odoo-module */

import * as ErrorPopup from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PreparationDisplayTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            // First order should send these orderlines to preparation:
            // - Letter Tray x10
            ProductScreen.confirmOpeningPopup(),

            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "10.0"),
            ProductScreen.addOrderline("Magnetic Board", "5"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "5.0"),
            ProductScreen.addOrderline("Monitor Stand", "1"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),

            ReceiptScreen.clickNextOrder(),

            // Should not send anything to preparation
            ProductScreen.addOrderline("Magnetic Board", "5"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "5.0"),
            ProductScreen.addOrderline("Monitor Stand", "1"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.0"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),

            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationDisplayPrinterTour", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.addOrderline("Letter Tray"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            //This steps is making sure that we atleast tried to call the printer
            ErrorPopup.clickConfirm(),
        ].flat(),
});
