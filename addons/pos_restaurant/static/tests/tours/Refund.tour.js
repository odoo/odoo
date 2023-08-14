/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("RefundStayCurrentTableTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();
        ProductScreen.do.confirmOpeningPopup();

        // Create first order and pay it
        FloorScreen.do.clickTable("2");
        ProductScreen.do.clickDisplayedProduct("Coca-Cola");
        ProductScreen.check.selectedOrderlineHas("Coca-Cola");
        ProductScreen.do.clickDisplayedProduct("Coca-Cola");
        ProductScreen.check.selectedOrderlineHas("Coca-Cola");
        ProductScreen.do.clickDisplayedProduct("Water");
        ProductScreen.check.selectedOrderlineHas("Water");
        ProductScreen.check.totalAmountIs("6.60");
        ProductScreen.do.clickPayButton();
        PaymentScreen.do.clickPaymentMethod("Cash");
        PaymentScreen.do.clickValidate();
        ReceiptScreen.do.clickNextOrder();

        // Go to another table and refund one of the products
        FloorScreen.do.clickTable("4");
        ProductScreen.check.orderIsEmpty();
        ProductScreen.do.clickRefund();
        TicketScreen.do.selectOrder("-0001");
        TicketScreen.check.hasLine({
            productName: "Coca-Cola",
        });
        ProductScreen.do.pressNumpad("2");
        TicketScreen.check.toRefundTextContains("To Refund: 2.00");
        TicketScreen.do.confirmRefund();
        ProductScreen.check.isShown();
        ProductScreen.check.selectedOrderlineHas("Coca-Cola");
        ProductScreen.check.totalAmountIs("-4.40");

        return getSteps();
    },
});
