/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { Chrome } from "@pos_restaurant/../tests/tours/helpers/ChromeTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { ProductScreen } from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import { SplitBillScreen } from "@pos_restaurant/../tests/tours/helpers/SplitBillScreenTourMethods";
import { TicketScreen } from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import { combo } from "@point_of_sale/../tests/tours/helpers/ComboPopupMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SplitBillScreenTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        // signal to start generating steps
        // when finished, steps can be taken from getSteps
        startSteps();

        ProductScreen.do.confirmOpeningPopup();
        FloorScreen.do.clickTable("2");
        ProductScreen.exec.addOrderline("Water", "5", "2", "10.0");
        ProductScreen.exec.addOrderline("Minute Maid", "3", "2", "6.0");
        ProductScreen.exec.addOrderline("Coca-Cola", "1", "2", "2.0");
        ProductScreen.do.clickSplitBillButton();

        // Check if the screen contains all the orderlines
        SplitBillScreen.check.orderlineHas("Water", "5", "0");
        SplitBillScreen.check.orderlineHas("Minute Maid", "3", "0");
        SplitBillScreen.check.orderlineHas("Coca-Cola", "1", "0");

        // split 3 water and 1 coca-cola
        SplitBillScreen.do.clickOrderline("Water");
        SplitBillScreen.check.orderlineHas("Water", "5", "1");
        SplitBillScreen.do.clickOrderline("Water");
        SplitBillScreen.do.clickOrderline("Water");
        SplitBillScreen.check.orderlineHas("Water", "5", "3");
        SplitBillScreen.check.subtotalIs("6.0");
        SplitBillScreen.do.clickOrderline("Coca-Cola");
        SplitBillScreen.check.orderlineHas("Coca-Cola", "1", "1");
        SplitBillScreen.check.subtotalIs("8.0");

        // click pay to split, go back to check the lines
        SplitBillScreen.do.clickPay();
        PaymentScreen.do.clickBack();
        ProductScreen.do.clickOrderline("Water", "3.0");
        ProductScreen.do.clickOrderline("Coca-Cola", "1.0");

        // go back to the original order and see if the order is changed
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.selectOrder("-0001");
        TicketScreen.do.loadSelectedOrder();
        ProductScreen.check.isShown();
        ProductScreen.do.clickOrderline("Water", "2.0");
        ProductScreen.do.clickOrderline("Minute Maid", "3.0");
        return getSteps();
    },
});

registry.category("web_tour.tours").add("SplitBillScreenTour2", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.confirmOpeningPopup();
        FloorScreen.do.clickTable("2");
        ProductScreen.exec.addOrderline("Water", "1", "2.0");
        ProductScreen.exec.addOrderline("Minute Maid", "1", "2.0");
        ProductScreen.exec.addOrderline("Coca-Cola", "1", "2.0");
        Chrome.do.backToFloor();
        FloorScreen.do.clickTable("2");
        ProductScreen.do.clickSplitBillButton();

        SplitBillScreen.do.clickOrderline("Water");
        SplitBillScreen.check.orderlineHas("Water", "1", "1");
        SplitBillScreen.do.clickOrderline("Coca-Cola");
        SplitBillScreen.check.orderlineHas("Coca-Cola", "1", "1");
        SplitBillScreen.do.clickPay();
        PaymentScreen.do.clickBack();
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.selectOrder("-0002");
        TicketScreen.do.loadSelectedOrder();
        ProductScreen.do.clickOrderline("Water", "1.0");
        ProductScreen.do.clickOrderline("Coca-Cola", "1.0");
        ProductScreen.check.totalAmountIs("4.00");
        Chrome.do.clickMenuButton();
        Chrome.do.clickTicketButton();
        TicketScreen.do.selectOrder("-0001");
        TicketScreen.do.loadSelectedOrder();
        Order.hasLine({ productName: "Minute Maid", quantity: "1.0", withClass: ".selected" });
        ProductScreen.check.totalAmountIs("2.00");
        return getSteps();
    },
});

registry.category("web_tour.tours").add("SplitBillScreenTour3", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();
        ProductScreen.do.confirmOpeningPopup();
        FloorScreen.do.clickTable("2");
        ProductScreen.exec.addOrderline("Water", "2", "2", "4.00");
        ProductScreen.do.clickSplitBillButton();

        // Check if the screen contains all the orderlines
        SplitBillScreen.check.orderlineHas("Water", "2", "0");

        // split 1 water
        SplitBillScreen.do.clickOrderline("Water");
        SplitBillScreen.check.orderlineHas("Water", "2", "1");
        SplitBillScreen.check.subtotalIs("2.0");

        // click pay to split, and pay
        SplitBillScreen.do.clickPay();
        PaymentScreen.do.clickPaymentMethod("Bank");
        PaymentScreen.do.clickValidate();
        // Check if the receiptscreen suggests us to continue the order
        ReceiptScreen.do.clickContinueOrder();

        // Check if there is still water in the order
        ProductScreen.check.isShown();
        ProductScreen.check.selectedOrderlineHas("Water", "1.0");
        ProductScreen.do.clickPayButton(true);
        PaymentScreen.do.clickPaymentMethod("Bank");
        PaymentScreen.do.clickValidate();
        // Check if there is no more order to continue
        ReceiptScreen.do.clickNextOrder();

        return getSteps();
    },
});

registry.category("web_tour.tours").add("SplitBillScreenTour4PosCombo", {
    test: true,
    url: "/pos/ui",
    steps: () => [
        ...ProductScreen.do.confirmOpeningPopup(),
        ...FloorScreen.do.clickTable("2"),

        ...ProductScreen.do.clickHomeCategory(),
        ...ProductScreen.do.clickDisplayedProduct("Office Combo"),
        combo.select("Combo Product 3"),
        combo.select("Combo Product 5"),
        combo.select("Combo Product 8"),
        combo.confirm(),

        ...ProductScreen.do.clickDisplayedProduct("Office Combo"),
        combo.select("Combo Product 2"),
        combo.select("Combo Product 4"),
        combo.select("Combo Product 7"),
        combo.confirm(),

        ...ProductScreen.exec.addOrderline("Water", "1"),
        ...ProductScreen.exec.addOrderline("Minute Maid", "1"),

        // The water and the first combo will go in the new splitted order
        // we will then check if the rest of the items from this combo
        // are automatically sent to the new order.
        ...ProductScreen.do.clickSplitBillButton(),
        ...SplitBillScreen.do.clickOrderline("Water"),
        ...SplitBillScreen.do.clickOrderline("Combo Product 3"),
        // we check that all the lines in the combo are splitted together
        ...SplitBillScreen.check.orderlineHas("Water", "1", "1"),
        ...SplitBillScreen.check.orderlineHas("Office Combo", "1", "1"),
        ...SplitBillScreen.check.orderlineHas("Combo Product 3", "1", "1"),
        ...SplitBillScreen.check.orderlineHas("Combo Product 5", "1", "1"),
        ...SplitBillScreen.check.orderlineHas("Combo Product 8", "1", "1"),
        ...SplitBillScreen.check.orderlineHas("Office Combo", "1", "1"),
        ...SplitBillScreen.check.orderlineHas("Combo Product 2", "1", "0"),
        ...SplitBillScreen.check.orderlineHas("Combo Product 4", "1", "0"),
        ...SplitBillScreen.check.orderlineHas("Combo Product 7", "1", "0"),

        ...SplitBillScreen.check.subtotalIs("52.13"),
        ...SplitBillScreen.do.clickPay(),
        ...PaymentScreen.do.clickPaymentMethod("Bank"),
        ...PaymentScreen.do.clickValidate(),
        ...ReceiptScreen.do.clickContinueOrder(),
        // Check if there is still water in the order
        ...ProductScreen.check.isShown(),
        // now we check that all the lines that remained in the order are correct
        ...ProductScreen.check.selectedOrderlineHas("Minute Maid", "1.0"),
        ...ProductScreen.do.clickOrderline("Office Combo"),
        ...ProductScreen.do.clickOrderline("Combo Product 2"),
        ...ProductScreen.check.selectedOrderlineHas(
            "Combo Product 2",
            "1.0",
            "6.15",
            "Office Combo"
        ),
        ...ProductScreen.do.clickOrderline("Combo Product 4"),
        ...ProductScreen.check.selectedOrderlineHas(
            "Combo Product 4",
            "1.0",
            "13.54",
            "Office Combo"
        ),
        ...ProductScreen.do.clickOrderline("Combo Product 7"),
        ...ProductScreen.check.selectedOrderlineHas(
            "Combo Product 7",
            "1.0",
            "20.31",
            "Office Combo"
        ),
        ...ProductScreen.check.totalAmountIs("42.53"),
    ],
});
