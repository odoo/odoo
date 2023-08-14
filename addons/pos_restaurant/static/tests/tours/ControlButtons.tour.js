/** @odoo-module */

import { TextAreaPopup } from "@point_of_sale/../tests/tours/helpers/TextAreaPopupTourMethods";
import { NumberPopup } from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import { Chrome } from "@pos_restaurant/../tests/tours/helpers/ChromeTourMethods";
import { FloorScreen } from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import { ProductScreen } from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
import { SplitBillScreen } from "@pos_restaurant/../tests/tours/helpers/SplitBillScreenTourMethods";
import { BillScreen } from "@pos_restaurant/../tests/tours/helpers/BillScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ControlButtonsTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        // signal to start generating steps
        // when finished, steps can be taken from getSteps
        startSteps();

        // Test TransferOrderButton
        FloorScreen.do.clickTable("2");
        ProductScreen.exec.addOrderline("Water", "5", "2", "10.0");
        ProductScreen.do.clickTransferButton();
        FloorScreen.do.clickTable("4");
        Chrome.do.backToFloor();
        FloorScreen.do.clickTable("2");
        ProductScreen.check.orderIsEmpty();
        Chrome.do.backToFloor();
        FloorScreen.do.clickTable("4");

        // Test SplitBillButton
        ProductScreen.do.clickSplitBillButton();
        SplitBillScreen.do.clickBack();

        // Test OrderlineNoteButton
        ProductScreen.do.clickNoteButton();
        TextAreaPopup.check.isShown();
        TextAreaPopup.do.inputText("test note");
        TextAreaPopup.do.clickConfirm();
        Order.hasLine({
            productName: "Water",
            quantity: "5",
            price: "10.0",
            customerNote: "test note",
            withClass: ".selected",
        });
        ProductScreen.exec.addOrderline("Water", "8", "1", "8.0");

        // Test PrintBillButton
        ProductScreen.do.clickPrintBillButton();
        BillScreen.check.isShown();
        BillScreen.do.clickOk();

        // Test GuestButton
        ProductScreen.do.clickGuestButton();
        NumberPopup.do.enterValue("15");
        NumberPopup.check.inputShownIs("15");
        NumberPopup.do.clickConfirm();
        ProductScreen.check.guestNumberIs("15");

        ProductScreen.do.clickGuestButton();
        NumberPopup.do.enterValue("5");
        NumberPopup.check.inputShownIs("5");
        NumberPopup.do.clickConfirm();
        ProductScreen.check.guestNumberIs("5");

        return getSteps();
    },
});
