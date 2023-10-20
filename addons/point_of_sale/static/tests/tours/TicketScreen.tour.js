/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as PartnerListScreen from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as ErrorPopup from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("TicketScreenTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.deleteOrder("-0002"),
            Chrome.confirmPopup(),
            TicketScreen.clickDiscard(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.deleteOrder("-0001"),
            Chrome.confirmPopup(),
            TicketScreen.clickDiscard(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(2, "-0003"),
            TicketScreen.clickDiscard(),
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Nicole Ford"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(2, "Nicole Ford", false),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Brandon Freeman"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(3, "Brandon Freeman", false),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "2", "4"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(4, "Receipt"),
            TicketScreen.selectFilter("Receipt"),
            TicketScreen.nthRowContains(2, "Receipt"),
            TicketScreen.selectFilter("Payment"),
            TicketScreen.nthRowContains(2, "Payment"),
            TicketScreen.selectFilter("Ongoing"),
            TicketScreen.nthRowContains(2, "Ongoing"),
            TicketScreen.selectFilter("All active orders"),
            TicketScreen.nthRowContains(4, "Receipt"),
            TicketScreen.search("Customer", "Nicole"),
            TicketScreen.nthRowContains(2, "Nicole", false),
            TicketScreen.search("Customer", "Brandon"),
            TicketScreen.nthRowContains(2, "Brandon", false),
            TicketScreen.search("Receipt Number", "-0005"),
            TicketScreen.nthRowContains(2, "Receipt"),
            // Close the TicketScreen to see the current order which is in ReceiptScreen.
            // This is just to remove the search string in the search bar.
            TicketScreen.clickDiscard(),
            ReceiptScreen.isShown(),
            // Open again the TicketScreen to check the Paid filter.
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.nthRowContains(2, "-0005"),
            TicketScreen.selectOrder("-0005"),
            TicketScreen.clickControlButton("Print Receipt"),
            TicketScreen.receiptTotalIs("8.00"),
            ReceiptScreen.clickBack(),
            TicketScreen.clickBackToMainTicketScreen(),
            // Pay the order that was in PaymentScreen.
            TicketScreen.selectFilter("Payment"),
            TicketScreen.selectOrder("-0004"),
            TicketScreen.loadSelectedOrder(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.isShown(),
            // Check that the Paid filter will show the 2 synced orders.
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.nthRowContains(2, "Brandon Freeman", false),
            TicketScreen.nthRowContains(3, "-0005"),
            // Invoice order
            TicketScreen.selectOrder("-0005"),
            inLeftSide(Order.hasLine()),
            TicketScreen.clickControlButton("Invoice"),
            Chrome.confirmPopup(),
            PartnerListScreen.isShown(),
            PartnerListScreen.clickPartner("Colleen Diaz"),
            TicketScreen.invoicePrinted(),
            TicketScreen.clickBackToMainTicketScreen(),
            TicketScreen.partnerIs("Colleen Diaz"),
            // Reprint receipt
            TicketScreen.clickControlButton("Print Receipt"),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickBack(),
            TicketScreen.clickBackToMainTicketScreen(),
            // When going back, the ticket screen should be in its previous state.
            TicketScreen.filterIs("Paid"),
            // Test refund //
            TicketScreen.clickDiscard(),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickRefund(),
            // Filter should be automatically 'Paid'.
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("-0005"),
            TicketScreen.partnerIs("Colleen Diaz"),
            inLeftSide(Order.hasLine({ productName: "Desk Pad", withClass: ".selected" })),
            ProductScreen.pressNumpad("3"),
            // Error should show because 2 is more than the number
            // that can be refunded.
            ErrorPopup.clickConfirm(),
            TicketScreen.clickDiscard(),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0005"),
            inLeftSide(Order.hasLine({ productName: "Desk Pad", withClass: ".selected" })),
            ProductScreen.pressNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.isShown(),
            ProductScreen.selectedOrderlineHas("Desk Pad", "-1.00"),
            // Try changing the refund line to positive number.
            // Error popup should show.
            ProductScreen.pressNumpad("2"),
            ErrorPopup.clickConfirm(),
            // Change the refund line quantity to -3 -- not allowed
            // so error popup.
            ProductScreen.pressNumpad("+/-", "3"),
            ErrorPopup.clickConfirm(),
            // Change the refund line quantity to -2 -- allowed.
            ProductScreen.pressNumpad("+/-", "2"),
            ProductScreen.selectedOrderlineHas("Desk Pad", "-2.00"),
            // Check if the amount being refunded changed to 2.
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0005"),
            TicketScreen.toRefundTextContains("Refunding 2.00"),
            TicketScreen.clickDiscard(),
            ProductScreen.goBackToMainScreen(),
            // Pay the refund order.
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            // Check refunded quantity.
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0005"),
            TicketScreen.refundedNoteContains("2.00 Refunded"),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionNoTaxRefund", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.changeFiscalPosition("No Tax"),
            ProductScreen.totalAmountIs("86.96"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.00"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.pressNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.goBackToMainScreen(),
            ProductScreen.totalAmountIs("-86.96"),
        ].flat(),
});

registry.category("web_tour.tours").add("LotRefundTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("123456789"),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.pressNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.clickLotIcon(),
            ProductScreen.checkFirstLotNumber("123456789"),
        ].flat(),
});
