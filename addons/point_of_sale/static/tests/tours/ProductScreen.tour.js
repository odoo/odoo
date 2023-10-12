/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { TextAreaPopup } from "@point_of_sale/../tests/tours/helpers/TextAreaPopupTourMethods";
import { getSteps, startSteps, insertSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

registry.category("web_tour.tours").add("ProductScreenTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        // signal to start generating steps
        // when finished, steps can be taken from getSteps
        startSteps();

        // Go by default to home category
        ProductScreen.do.clickHomeCategory();

        // Clicking product multiple times should increment quantity
        ProductScreen.do.clickDisplayedProduct("Desk Organizer");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "1.0", "5.10");
        ProductScreen.do.clickDisplayedProduct("Desk Organizer");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "2.0", "10.20");

        // Clicking product should add new orderline and select the orderline
        // If orderline exists, increment the quantity
        ProductScreen.do.clickDisplayedProduct("Letter Tray");
        ProductScreen.check.selectedOrderlineHas("Letter Tray", "1.0", "5.28");
        ProductScreen.do.clickDisplayedProduct("Desk Organizer");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "3.0", "15.30");

        // Check effects of clicking numpad buttons
        ProductScreen.do.clickOrderline("Letter Tray", "1");
        ProductScreen.check.selectedOrderlineHas("Letter Tray", "1.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Letter Tray", "0.0", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "3", "15.30");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "0.0", "0.0");
        ProductScreen.do.pressNumpad("1");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "1.0", "5.1");
        ProductScreen.do.pressNumpad("2");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "12.0", "61.2");
        ProductScreen.do.pressNumpad("3");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "123.0", "627.3");
        ProductScreen.do.pressNumpad(".", "5");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "123.5", "629.85");
        ProductScreen.do.pressNumpad("Price");
        ProductScreen.check.modeIsActive("Price");
        ProductScreen.do.pressNumpad("1");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "123.5", "123.5");
        ProductScreen.do.pressNumpad("1", ".");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "123.5", "1,358.5");
        ProductScreen.do.pressNumpad("% Disc");
        ProductScreen.check.modeIsActive("% Disc");
        ProductScreen.do.pressNumpad("5", ".");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "123.5", "1,290.58");
        ProductScreen.do.pressNumpad("Qty");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.orderIsEmpty();

        // Check different subcategories
        ProductScreen.do.clickSubcategory("Desks");
        ProductScreen.check.productIsDisplayed("Desk Pad");
        ProductScreen.do.clickHomeCategory();
        ProductScreen.do.clickSubcategory("Misc");
        ProductScreen.check.productIsDisplayed("Whiteboard Pen");
        ProductScreen.do.clickHomeCategory();
        ProductScreen.do.clickSubcategory("Chairs");
        ProductScreen.check.productIsDisplayed("Letter Tray");
        ProductScreen.do.clickHomeCategory();

        // Add two orderlines and update quantity
        ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
        ProductScreen.do.clickDisplayedProduct("Wall Shelf Unit");
        ProductScreen.do.clickOrderline("Whiteboard Pen", "1.0");
        ProductScreen.do.pressNumpad("2");
        ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "2.0");
        ProductScreen.do.clickOrderline("Wall Shelf Unit", "1.0");
        ProductScreen.do.pressNumpad("2");
        ProductScreen.check.selectedOrderlineHas("Wall Shelf Unit", "2.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Wall Shelf Unit", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "2.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.orderIsEmpty();

        // Add multiple orderlines then delete each of them until empty
        ProductScreen.do.clickDisplayedProduct("Whiteboard Pen");
        ProductScreen.do.clickDisplayedProduct("Wall Shelf Unit");
        ProductScreen.do.clickDisplayedProduct("Small Shelf");
        ProductScreen.do.clickDisplayedProduct("Magnetic Board");
        ProductScreen.do.clickDisplayedProduct("Monitor Stand");
        ProductScreen.do.clickOrderline("Whiteboard Pen", "1.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Whiteboard Pen", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Monitor Stand", "1.0");
        ProductScreen.do.clickOrderline("Wall Shelf Unit", "1.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Wall Shelf Unit", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Monitor Stand", "1.0");
        ProductScreen.do.clickOrderline("Small Shelf", "1.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Small Shelf", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Monitor Stand", "1.0");
        ProductScreen.do.clickOrderline("Magnetic Board", "1.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Magnetic Board", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Monitor Stand", "1.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.selectedOrderlineHas("Monitor Stand", "0.0");
        ProductScreen.do.pressNumpad("⌫");
        ProductScreen.check.orderIsEmpty();

        // Test OrderlineCustomerNoteButton
        ProductScreen.do.clickDisplayedProduct("Desk Organizer");
        ProductScreen.check.selectedOrderlineHas("Desk Organizer", "1.0");
        ProductScreen.do.clickOrderlineCustomerNoteButton();
        TextAreaPopup.check.isShown();
        TextAreaPopup.do.inputText("Test customer note");
        TextAreaPopup.do.clickConfirm();
        Order.hasLine({
            productName: "Desk Organizer",
            quantity: "1.0",
            customerNote: "Test customer note",
            withClass: ".selected",
        });
        ProductScreen.check.isShown();
        return getSteps();
    },
});

registry.category("web_tour.tours").add("FiscalPositionNoTax", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.clickHomeCategory();
        ProductScreen.do.clickDisplayedProduct("Test Product");
        ProductScreen.check.totalAmountIs("100.00");
        ProductScreen.do.changeFiscalPosition("No Tax");
        ProductScreen.check.noDiscountApplied("100.00");
        ProductScreen.check.totalAmountIs("86.96");
        ProductScreen.do.clickPayButton();
        PaymentScreen.do.clickPaymentMethod("Bank");
        PaymentScreen.check.remainingIs("0.00");
        PaymentScreen.do.clickValidate();
        ReceiptScreen.check.isShown();
        insertSteps(Order.doesNotHaveLine({ discount: "" }));
        return getSteps();
    },
});

registry.category("web_tour.tours").add("CashClosingDetails", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.enterOpeningAmount("90");
        ProductScreen.do.confirmOpeningPopup();
        ProductScreen.check.checkSecondCashClosingDetailsLineAmount("10.00", "-");
        return getSteps();
    },
});

registry.category("web_tour.tours").add("ShowTaxExcludedTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.confirmOpeningPopup();

        ProductScreen.do.clickHomeCategory();

        ProductScreen.do.clickDisplayedProduct("Test Product");
        ProductScreen.check.selectedOrderlineHas("Test Product", "1.0", "100.0");
        ProductScreen.check.totalAmountIs("110.0");
        return getSteps();
    },
});
