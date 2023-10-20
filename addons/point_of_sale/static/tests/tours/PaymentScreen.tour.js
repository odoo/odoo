/** @odoo-module */

import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PaymentScreenTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "10.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.emptyPaymentlines("52.8"),

            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "11"),
            PaymentScreen.selectedPaymentlineHas("Cash", "11.00"),
            PaymentScreen.remainingIs("41.8"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(false),
            // remove the selected paymentline with multiple backspace presses
            PaymentScreen.pressNumpad("⌫ ⌫"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "0"),
            PaymentScreen.selectedPaymentlineHas("Cash", "0.00"),
            PaymentScreen.clickPaymentlineDelButton("Cash", "0", true),
            PaymentScreen.emptyPaymentlines("52.8"),

            // Pay with bank, the selected line should have full amount
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            // remove the line using the delete button
            PaymentScreen.clickPaymentlineDelButton("Bank", "52.8"),

            // Use +10 and +50 to increment the amount of the paymentline
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.pressNumpad("+10"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "10"),
            PaymentScreen.remainingIs("42.8"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.pressNumpad("+50"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "60"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("7.2"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickPaymentlineDelButton("Cash", "60.0"),

            // Multiple paymentlines
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.pressNumpad("1"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "1"),
            PaymentScreen.remainingIs("51.8"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.fillPaymentLineAmountMobile("Bank", "5"),
            PaymentScreen.pressNumpad("5"),
            PaymentScreen.remainingIs("46.8"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenTour2", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Letter Tray", "1", "10"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.enterPaymentLineAmount("Bank", "1000"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenRoundingUp", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("2.00"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),

            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),

            ProductScreen.addOrderline("Product Test", "-1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("-2.00"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenRoundingDown", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.95"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),

            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),

            ProductScreen.addOrderline("Product Test", "-1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("-1.95"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenRoundingHalfUp", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Product Test 1.2", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.00"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),

            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),

            ProductScreen.addOrderline("Product Test 1.25", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.5"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),

            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),

            ProductScreen.addOrderline("Product Test 1.4", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.5"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),

            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),

            ProductScreen.addOrderline("Product Test 1.2", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.00"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.pressNumpad("2"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "2"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("1.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenRoundingHalfUpCashAndBank", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Product Test 40", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Nicole Ford"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("40.00"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.pressNumpad("3 8"),
            PaymentScreen.fillPaymentLineAmountMobile("Bank", "38"),
            PaymentScreen.remainingIs("2.0"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),

            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.clickNextOrder(),

            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Product Test 41", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Nicole Ford"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("41.00"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.pressNumpad("3 8"),
            PaymentScreen.fillPaymentLineAmountMobile("Bank", "38"),
            PaymentScreen.remainingIs("3.0"),
            PaymentScreen.clickPaymentMethod("Cash"),

            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("0.0"),

            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenTotalDueWithOverPayment", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPayButton(),

            PaymentScreen.totalIs("1.95"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "5"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.changeIs("3.05"),
            PaymentScreen.totalDueIs("1.95"),
        ].flat(),
});
