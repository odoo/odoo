/** @odoo-module */

import * as TextInputPopup from "@point_of_sale/../tests/tours/helpers/TextInputPopupTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as NumberPopup from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/helpers/SplitBillScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ControlButtonsTour", {
    test: true,
    steps: () =>
        [
            // Test TransferOrderButton
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            ProductScreen.controlButtonMore(),
            ProductScreen.controlButton("Transfer"),
            FloorScreen.clickTable("4"),
            FloorScreen.backToFloor(),
            FloorScreen.clickTable("2"),
            ProductScreen.orderIsEmpty(),
            FloorScreen.backToFloor(),
            FloorScreen.clickTable("4"),

            // Test SplitBillButton
            ProductScreen.controlButtonMore(),
            ProductScreen.controlButton("Split"),
            SplitBillScreen.clickBack(),

            ProductScreen.controlButtonMore(),
            ProductScreen.controlButton("Internal Note"),
            TextInputPopup.inputText("test note"),
            Dialog.confirm(),
            Order.hasLine({
                productName: "Water",
                quantity: "5",
                price: "10.0",
                internalNote: "test note",
                withClass: ".selected",
            }),
            ProductScreen.addOrderline("Water", "8", "1", "8.0"),

            // Test PrintBillButton
            ProductScreen.controlButton("Bill"),
            Dialog.is({ title: "Bill Printing" }),
            Dialog.cancel(),

            // Test GuestButton
            ProductScreen.controlButtonMore(),
            ProductScreen.controlButton("Guests"),
            NumberPopup.enterValue("15"),
            NumberPopup.isShown("15"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("15"),

            ProductScreen.controlButton("Guests"),
            NumberPopup.enterValue("5"),
            NumberPopup.isShown("5"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("5"),
        ].flat(),
});
