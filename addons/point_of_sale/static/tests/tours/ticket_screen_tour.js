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
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Create an order
            ProductScreen.addOrderline("Desk Pad", "4"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // Test invoicing for paid order
            Chrome.clickMenuOption("Orders"),
            TicketScreen.selectOrder("-0001"),
            // inLeftSide(Order.hasLine()),
            Order.hasLine(),
            TicketScreen.clickControlButton("Invoice"),
            Dialog.confirm(),
            PartnerList.clickPartner("Partner Test 3"),
            TicketScreen.invoicePrinted(),
            { ...ProductScreen.back(), isActive: ["mobile"] },

            // Test Reprint receipt
            TicketScreen.clickControlButton("Print Receipt"),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickBack(),
            Chrome.clickFloatingOrder("2"),

            // Test refund
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            //Filter should be automatically 'Paid'.
            TicketScreen.selectOrder("-0001"),
            ...Order.hasLine({ productName: "Desk Pad", withClass: ".selected" }),
            Numpad.click("5"),
            // Line only has 4 quantity, so error popup should show.
            Dialog.confirm(),
            Order.hasLine({ productName: "Desk Pad", withClass: ".selected" }),
            Numpad.click("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.selectedOrderlineHas("Desk Pad", "-1.00"),
            inLeftSide([
                // Try changing the refund line to positive number.
                // Error popup should show.
                Numpad.click("2"),
                Dialog.confirm(),
                // Change the refund line quantity to -6 -- not allowed
                // so error popup.
                ...["+/-", "6"].map(Numpad.click),
                Dialog.confirm(),
            ]),
            // Change the refund line quantity to -2 -- allowed.
            ProductScreen.clickNumpad("+/-", "2"),
            ProductScreen.selectedOrderlineHas("Desk Pad", "-2.00"),
            // Pay the refund order.
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            // Check refunded quantity.
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            TicketScreen.refundedNoteContains("2.00 Refunded"),
        ].flat(),
});

registry.category("web_tour.tours").add("FiscalPositionNoTaxRefund", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
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
            Numpad.click("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.totalAmountIs("100.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("LotRefundTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
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
            Numpad.click("1"),
            TicketScreen.toRefundTextContains("To Refund: 1.00"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.clickLotIcon(),
            ProductScreen.checkFirstLotNumber("123456789"),
        ].flat(),
});

registry.category("web_tour.tours").add("RefundFewQuantities", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Sugar"),
            ProductScreen.clickNumpad("0", "."),
            ProductScreen.selectedOrderlineHas("Sugar", "0.00", "0.00"),
            ProductScreen.clickNumpad("0", "2"),
            ProductScreen.selectedOrderlineHas("Sugar", "0.02", "0.06"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            Numpad.enterValue("0.02"),
            TicketScreen.toRefundTextContains("To Refund: 0.02"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            Order.hasLine("Sugar", "-0.02", "-0.06"),
        ].flat(),
});
