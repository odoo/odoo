import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("TicketScreenTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Orders"),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.deleteOrder("-0002"),
            Dialog.confirm(),
            TicketScreen.clickDiscard(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.deleteOrder("-0001"),
            Dialog.confirm(),
            TicketScreen.clickDiscard(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(2, "-0003"),
            TicketScreen.clickDiscard(),
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(2, "Partner Test 1", false),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1", "3"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 2"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(3, "Partner Test 2", false),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "2", "4"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(4, "Receipt"),
            TicketScreen.selectFilter("Receipt"),
            TicketScreen.nthRowContains(2, "Receipt"),
            TicketScreen.selectFilter("Payment"),
            TicketScreen.nthRowContains(2, "Payment"),
            TicketScreen.selectFilter("Ongoing"),
            TicketScreen.nthRowContains(2, "Ongoing"),
            TicketScreen.selectFilter("All active orders"),
            TicketScreen.nthRowContains(4, "Receipt"),
            TicketScreen.search("Receipt Number", "-0005"),
            TicketScreen.nthRowContains(2, "Receipt"),
            TicketScreen.search("Customer", "Partner Test 1"),
            TicketScreen.nthRowContains(2, "Partner Test 1", false),
            TicketScreen.search("Customer", "Partner Test 2"),
            TicketScreen.nthRowContains(2, "Partner Test 2", false),
            // Close the TicketScreen to see the current order which is in ReceiptScreen.
            // This is just to remove the search string in the search bar.
            TicketScreen.clickDiscard(),
            ReceiptScreen.isShown(),
            // Open again the TicketScreen to check the Paid filter.
            Chrome.clickMenuOption("Orders"),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.nthRowContains(2, "-0005"),
            TicketScreen.selectOrder("-0005"),
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
            Chrome.clickMenuOption("Orders"),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.nthRowContains(2, "Partner Test 2", false),
            TicketScreen.nthRowContains(3, "-0005"),
            // Invoice order
            TicketScreen.selectOrder("-0005"),
            inLeftSide(Order.hasLine()),
            TicketScreen.clickControlButton("Invoice"),
            Dialog.confirm(),
            PartnerList.clickPartner("Partner Test 3"),
            TicketScreen.invoicePrinted(),
            TicketScreen.back(),
            // When going back, the ticket screen should be in its previous state.
            TicketScreen.filterIs("Paid"),
            // Test refund //
            TicketScreen.clickDiscard(),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            //Filter should be automatically 'Paid'.
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("-0005"),
            inLeftSide([
                ...Order.hasLine({ productName: "Desk Pad", withClass: ".selected" }),
                Numpad.click("3"),
                Dialog.confirm(),
            ]),
            TicketScreen.clickDiscard(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0005"),
            inLeftSide(Order.hasLine({ productName: "Desk Pad", withClass: ".selected" })),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.isShown(),
            inLeftSide([
                ...ProductScreen.clickLine("Desk Pad"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "-1.00"),
                // Try changing the refund line to positive number.
                // Error popup should show.
                Numpad.click("2"),
                Dialog.confirm(),
                // Change the refund line quantity to -3 -- not allowed
                // so error popup.
                ...["+/-", "3"].map(Numpad.click),
                Dialog.confirm(),
                // Change the refund line quantity to -2 -- allowed.
                ...["+/-", "2"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "-2.00"),
            ]),
            // Check if the amount being refunded changed to 2.
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0005"),
            TicketScreen.toRefundTextContains("Refunding 2.00"),
            TicketScreen.clickDiscard(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            // Pay the refund order.
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            // Check refunded quantity.
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0005"),
            TicketScreen.refundedNoteContains("2.00 Refunded"),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionNoTaxRefund", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickFiscalPosition("No Tax"),
            ProductScreen.totalAmountIs("100.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.totalAmountIs("100.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("LotRefundTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("123456789"),
            ProductScreen.selectedOrderlineHas("Product A", "1.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.clickLotIcon(),
            ProductScreen.checkFirstLotNumber("123456789"),
        ].flat(),
});

registry.category("web_tour.tours").add("RefundFewQuantities", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Sugar"),
            inLeftSide([
                ...["0", "."].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Sugar", "0.00", "0.00"),
                ...["0", "2"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Sugar", "0.02", "0.06"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("0", "."),
            ProductScreen.clickNumpad("0", "2"),
            TicketScreen.toRefundTextContains("To Refund: 0.02"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            Order.hasLine("Sugar", "-0.02", "-0.06"),
        ].flat(),
});
