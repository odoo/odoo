import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("TicketScreenTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            Chrome.newOrder(),
            ProductScreen.addOrderline("Desk Pad", "2", "4"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            // TicketScreen.clickControlButton("Print Receipt"),
            // // ......
            // TicketScreen.clickControlButton("Invoice"),
            // Dialog.confirm(),
            // TicketScreen.invoicePrinted(),
            { ...ProductScreen.back(), mobile: true },
            // Reprint receipt
            // TicketScreen.clickControlButton("Print Receipt"),
            // ReceiptScreen.isShown(),
            // ReceiptScreen.clickBack(),
            // TicketScreen.back(),
            // // When going back, the ticket screen should be in its previous state.
            // TicketScreen.filterIs("Paid"),
            // // Test refund //
            // TicketScreen.clickDiscard(),
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            //Filter should be automatically 'Paid'.
        ].flat(),
});

// registry.category("web_tour.tours").add("FiscalPositionNoTaxRefund", {
//     test: true,
//     steps: () =>
//         [
//             Dialog.confirm("Open session"),
//             ProductScreen.clickDisplayedProduct("Product Test"),
//             ProductScreen.totalAmountIs("100.00"),
//             ProductScreen.clickFiscalPosition("No Tax"),
//             ProductScreen.totalAmountIs("100.00"),
//             ProductScreen.clickPayButton(),
//             PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
//             PaymentScreen.clickValidate(),
//             ReceiptScreen.isShown(),
//             ReceiptScreen.clickNextOrder(),
//             ...ProductScreen.clickRefund(),
//             TicketScreen.selectOrder("-0001"),
//             ProductScreen.clickNumpad("1"),
//             TicketScreen.confirmRefund(),
//             ProductScreen.isShown(),
//             { ...ProductScreen.back(), isActive: ["mobile"] },
//             ProductScreen.totalAmountIs("100.00"),
//         ].flat(),
// });

// registry.category("web_tour.tours").add("LotRefundTour", {
//     test: true,
//     steps: () =>
//         [
//             Dialog.confirm("Open session"),
//             ProductScreen.clickDisplayedProduct("Product A"),
//             ProductScreen.enterLotNumber("123456789"),
//             ProductScreen.selectedOrderlineHas("Product A", "1.00"),
//             ProductScreen.clickPayButton(),
//             PaymentScreen.clickPaymentMethod("Bank"),
//             PaymentScreen.clickValidate(),
//             ReceiptScreen.isShown(),
//             ReceiptScreen.clickNextOrder(),
//             ...ProductScreen.clickRefund(),
//             TicketScreen.selectOrder("-0001"),
//             ProductScreen.clickNumpad("1"),
//             TicketScreen.toRefundTextContains("To Refund: 1.00"),
//             TicketScreen.confirmRefund(),
//             ProductScreen.isShown(),
//             ProductScreen.clickLotIcon(),
//             ProductScreen.checkFirstLotNumber("123456789"),
//         ].flat(),
// });

// registry.category("web_tour.tours").add("RefundFewQuantities", {
//     test: true,
//     steps: () =>
//         [
//             Dialog.confirm("Open session"),
//             ProductScreen.clickDisplayedProduct("Sugar"),
//             ProductScreen.clickNumpad("0", "."),
//             ProductScreen.selectedOrderlineHas("Sugar", "0.00", "0.00"),
//             ProductScreen.clickNumpad("0", "2"),
//             ProductScreen.selectedOrderlineHas("Sugar", "0.02", "0.06"),
//             ProductScreen.clickPayButton(),
//             PaymentScreen.clickPaymentMethod("Bank"),
//             PaymentScreen.clickValidate(),
//             ReceiptScreen.isShown(),
//             ReceiptScreen.clickNextOrder(),
//             ...ProductScreen.clickRefund(),
//             TicketScreen.selectOrder("-0001"),
//             ProductScreen.clickNumpad("0", "."),
//             ProductScreen.clickNumpad("0", "2"),
//             TicketScreen.toRefundTextContains("To Refund: 0.02"),
//             TicketScreen.confirmRefund(),
//             ProductScreen.isShown(),
//             Order.hasLine("Sugar", "-0.02", "-0.06"),
//         ].flat(),
// });
