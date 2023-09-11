/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { PartnerListScreen } from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { ErrorPopup } from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("TicketScreenTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();
        ProductScreen.do.confirmOpeningPopup();
        ProductScreen.do.clickHomeCategory();
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.clickNewTicket();
        ProductScreen.exec.addOrderline("Desk Pad", "1", "3");
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.deleteOrder("-0002");
        Chrome.do.confirmPopup();
        TicketScreen.do.clickDiscard();
        ProductScreen.check.orderIsEmpty();
        ProductScreen.exec.addOrderline("Desk Pad", "1", "2");
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.deleteOrder("-0001");
        Chrome.do.confirmPopup();
        TicketScreen.do.clickDiscard();
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.check.nthRowContains(2, "-0003");
        TicketScreen.do.clickDiscard();
        ProductScreen.exec.addOrderline("Desk Pad", "1", "2");
        ProductScreen.do.clickPartnerButton();
        ProductScreen.do.clickCustomer("Nicole Ford");
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.check.nthRowContains(2, "Nicole Ford", false);
        TicketScreen.do.clickNewTicket();
        ProductScreen.exec.addOrderline("Desk Pad", "1", "3");
        ProductScreen.do.clickPartnerButton();
        ProductScreen.do.clickCustomer("Brandon Freeman");
        ProductScreen.do.clickPayButton();
        PaymentScreen.check.isShown();
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.check.nthRowContains(3, "Brandon Freeman", false);
        TicketScreen.do.clickNewTicket();
        ProductScreen.exec.addOrderline("Desk Pad", "2", "4");
        ProductScreen.do.clickPayButton();
        PaymentScreen.do.clickPaymentMethod("Bank");
        PaymentScreen.do.clickValidate();
        ReceiptScreen.check.isShown();
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.check.nthRowContains(4, "Receipt");
        TicketScreen.do.selectFilter("Receipt");
        TicketScreen.check.nthRowContains(2, "Receipt");
        TicketScreen.do.selectFilter("Payment");
        TicketScreen.check.nthRowContains(2, "Payment");
        TicketScreen.do.selectFilter("Ongoing");
        TicketScreen.check.nthRowContains(2, "Ongoing");
        TicketScreen.do.selectFilter("All active orders");
        TicketScreen.check.nthRowContains(4, "Receipt");
        TicketScreen.do.search("Customer", "Nicole");
        TicketScreen.check.nthRowContains(2, "Nicole", false);
        TicketScreen.do.search("Customer", "Brandon");
        TicketScreen.check.nthRowContains(2, "Brandon", false);
        TicketScreen.do.search("Receipt Number", "-0005");
        TicketScreen.check.nthRowContains(2, "Receipt");
        // Close the TicketScreen to see the current order which is in ReceiptScreen.
        // This is just to remove the search string in the search bar.
        TicketScreen.do.clickDiscard();
        ReceiptScreen.check.isShown();
        // Open again the TicketScreen to check the Paid filter.
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.selectFilter("Paid");
        TicketScreen.check.nthRowContains(2, "-0005");
        TicketScreen.do.selectOrder("-0005");
        TicketScreen.do.clickControlButton("Print Receipt");
        TicketScreen.check.receiptTotalIs("8.00");
        ReceiptScreen.do.clickBack();
        TicketScreen.do.clickBackToMainTicketScreen();
        // Pay the order that was in PaymentScreen.
        TicketScreen.do.selectFilter("Payment");
        TicketScreen.do.selectOrder("-0004");
        TicketScreen.do.loadSelectedOrder();
        PaymentScreen.do.clickPaymentMethod("Cash");
        PaymentScreen.do.clickValidate();
        ReceiptScreen.check.isShown();
        ReceiptScreen.do.clickNextOrder();
        ProductScreen.check.isShown();
        // Check that the Paid filter will show the 2 synced orders.
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.selectFilter("Paid");
        TicketScreen.check.nthRowContains(2, "Brandon Freeman", false);
        TicketScreen.check.nthRowContains(3, "-0005");
        // Invoice order
        TicketScreen.do.selectOrder("-0005");
        TicketScreen.check.orderWidgetIsNotEmpty();
        TicketScreen.do.clickControlButton("Invoice");
        Chrome.do.confirmPopup();
        PartnerListScreen.check.isShown();
        PartnerListScreen.do.clickPartner("Colleen Diaz");
        TicketScreen.check.invoicePrinted();
        TicketScreen.do.clickBackToMainTicketScreen();
        TicketScreen.check.partnerIs("Colleen Diaz");
        // Reprint receipt
        TicketScreen.do.clickControlButton("Print Receipt");
        ReceiptScreen.check.isShown();
        ReceiptScreen.do.clickBack();
        TicketScreen.do.clickBackToMainTicketScreen();
        // When going back, the ticket screen should be in its previous state.
        TicketScreen.check.filterIs("Paid");
        // Test refund //
        TicketScreen.do.clickDiscard();
        ProductScreen.check.isShown();
        ProductScreen.check.orderIsEmpty();
        ProductScreen.do.clickRefund();
        // Filter should be automatically 'Paid'.
        TicketScreen.check.filterIs("Paid");
        TicketScreen.do.selectOrder("-0005");
        TicketScreen.check.partnerIs("Colleen Diaz");
        Order.hasLine({ productName: "Desk Pad", withClass: ".selected" });
        ProductScreen.do.pressNumpad("3");
        // Error should show because 2 is more than the number
        // that can be refunded.
        ErrorPopup.do.clickConfirm();
        TicketScreen.do.clickDiscard();
        ProductScreen.do.goBackToMainScreen();
        ProductScreen.check.isShown();
        ProductScreen.check.orderIsEmpty();
        ProductScreen.do.clickRefund();
        TicketScreen.do.selectOrder("-0005");
        Order.hasLine({ productName: "Desk Pad", withClass: ".selected" });
        ProductScreen.do.pressNumpad("1");
        TicketScreen.check.toRefundTextContains("To Refund: 1.00");
        TicketScreen.do.confirmRefund();
        ProductScreen.do.goBackToMainScreen();
        ProductScreen.check.isShown();
        ProductScreen.check.selectedOrderlineHas("Desk Pad", "-1.00");
        // Try changing the refund line to positive number.
        // Error popup should show.
        ProductScreen.do.pressNumpad("2");
        ErrorPopup.do.clickConfirm();
        // Change the refund line quantity to -3 -- not allowed
        // so error popup.
        ProductScreen.do.pressNumpad("+/-", "3");
        ErrorPopup.do.clickConfirm();
        // Change the refund line quantity to -2 -- allowed.
        ProductScreen.do.pressNumpad("+/-", "2");
        ProductScreen.check.selectedOrderlineHas("Desk Pad", "-2.00");
        // Check if the amount being refunded changed to 2.
        ProductScreen.do.clickRefund();
        TicketScreen.do.selectOrder("-0005");
        TicketScreen.check.toRefundTextContains("Refunding 2.00");
        TicketScreen.do.clickDiscard();
        ProductScreen.do.goBackToMainScreen();
        // Pay the refund order.
        ProductScreen.do.clickPayButton();
        PaymentScreen.do.clickPaymentMethod("Bank");
        PaymentScreen.do.clickValidate();
        ReceiptScreen.check.isShown();
        ReceiptScreen.do.clickNextOrder();
        // Check refunded quantity.
        ProductScreen.do.clickRefund();
        TicketScreen.do.selectOrder("-0005");
        TicketScreen.check.refundedNoteContains("2.00 Refunded");

        return getSteps();
    },
});


registry.category("web_tour.tours").add("FiscalPositionNoTaxRefund", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.confirmOpeningPopup();
        ProductScreen.do.clickHomeCategory();
        ProductScreen.do.clickDisplayedProduct('Product Test');
        ProductScreen.check.totalAmountIs('100.00');
        ProductScreen.do.changeFiscalPosition('No Tax');
        ProductScreen.check.totalAmountIs('86.96');
        ProductScreen.do.clickPayButton();
        PaymentScreen.do.clickPaymentMethod('Bank');
        PaymentScreen.check.remainingIs('0.00');
        PaymentScreen.do.clickValidate();
        ReceiptScreen.check.isShown();
        ReceiptScreen.do.clickNextOrder();
        ProductScreen.do.clickRefund();
        TicketScreen.do.selectOrder('-0001');
        ProductScreen.do.pressNumpad('1');
        TicketScreen.check.toRefundTextContains('To Refund: 1.00');
        TicketScreen.do.confirmRefund();
        ProductScreen.check.isShown();
        ProductScreen.do.goBackToMainScreen();
        ProductScreen.check.totalAmountIs('-86.96');

        return getSteps();
    }
});

registry.category("web_tour.tours").add("LotRefundTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();
        ProductScreen.do.confirmOpeningPopup();
        ProductScreen.do.clickHomeCategory();
        ProductScreen.do.clickDisplayedProduct('Product A');
        ProductScreen.do.enterLotNumber('123456789');
        ProductScreen.check.selectedOrderlineHas('Product A', '1.00');
        ProductScreen.do.clickPayButton();
        PaymentScreen.do.clickPaymentMethod('Bank');
        PaymentScreen.do.clickValidate();
        ReceiptScreen.check.isShown();
        ReceiptScreen.do.clickNextOrder();
        ProductScreen.do.clickRefund();
        TicketScreen.do.selectOrder('-0001');
        ProductScreen.do.pressNumpad('1');
        TicketScreen.check.toRefundTextContains('To Refund: 1.00');
        TicketScreen.do.confirmRefund();
        ProductScreen.check.isShown();
        ProductScreen.do.clickLotIcon();
        ProductScreen.check.checkFirstLotNumber('123456789');
        return getSteps();
    }
});
