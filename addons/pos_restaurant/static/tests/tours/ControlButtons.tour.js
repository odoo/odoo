/** @odoo-module */

import * as TextAreaPopup from "@point_of_sale/../tests/tours/helpers/TextAreaPopupTourMethods";
import * as NumberPopup from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/helpers/SplitBillScreenTourMethods";
import * as BillScreen from "@pos_restaurant/../tests/tours/helpers/BillScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ControlButtonsTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            // Test TransferOrderButton
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            ProductScreen.clickTransferButton(),
            FloorScreen.clickTable("4"),
            FloorScreen.backToFloor(),
            FloorScreen.clickTable("2"),
            ProductScreen.orderIsEmpty(),
            FloorScreen.backToFloor(),
            FloorScreen.clickTable("4"),

            // Test SplitBillButton
            ProductScreen.clickSplitBillButton(),
            SplitBillScreen.clickBack(),

            // Test OrderlineNoteButton
            ProductScreen.clickNoteButton(),
            TextAreaPopup.isShown(),
            TextAreaPopup.inputText("test note"),
            TextAreaPopup.clickConfirm(),
            Order.hasLine({
                productName: "Water",
                quantity: "5",
                price: "10.0",
                internalNote: "test note",
                withClass: ".selected",
            }),
            ProductScreen.addOrderline("Water", "8", "1", "8.0"),

            // Test PrintBillButton
            ProductScreen.clickPrintBillButton(),
            BillScreen.isShown(),
            BillScreen.clickOk(),

            // Test GuestButton
            ProductScreen.clickGuestButton(),
            NumberPopup.enterValue("15"),
            NumberPopup.inputShownIs("15"),
            NumberPopup.clickConfirm(),
            ProductScreen.guestNumberIs("15"),

            ProductScreen.clickGuestButton(),
            NumberPopup.enterValue("5"),
            NumberPopup.inputShownIs("5"),
            NumberPopup.clickConfirm(),
            ProductScreen.guestNumberIs("5"),
        ].flat(),
});
